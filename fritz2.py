import os
import time
import json
from collections import deque
from datetime import datetime
from fritzconnection import FritzConnection
from vfdwcn import WincorNixdorfDisplayFactory
import logging

# Logging einrichten
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# FRITZ!Box Zugangsdaten aus Umgebungsvariablen lesen
FRITZBOX_IP = os.getenv("FRITZBOX_IP", "192.168.0.1")
USERNAME = os.getenv("FRITZBOX_USER", "ulf")
PASSWORD = os.getenv("FRITZBOX_PASS", "rockula21")
DATA_FILE = "network_data.json"
max = 4294967296
# Verbindung zur FRITZ!Box herstellen
try:
    fc = FritzConnection(address=FRITZBOX_IP, user=USERNAME, password=PASSWORD)
except Exception as e:
    logging.error(f"Fehler beim Verbinden zur FRITZ!Box: {e}")
    exit(1)

# Display einrichten
factory = WincorNixdorfDisplayFactory()
VFDs = factory.get_vfd_wcn()
MyVFD = VFDs[0]
MyVFD.clearscreen()
MyVFD.set_charset(0x30)

# Ladebalken-Deque
load_d = deque([0x5F] * 8, maxlen=8)
load_u = deque([0x5F] * 8, maxlen=8)

# Netzwerkdaten abrufen
def get_network_data():
    try:
        downstream = fc.call_action("WANCommonIFC1", "GetTotalBytesReceived")["NewTotalBytesReceived"]
        upstream = fc.call_action("WANCommonIFC1", "GetTotalBytesSent")["NewTotalBytesSent"]
        return downstream, upstream
    except Exception as e:
        logging.error(f"Fehler beim Abrufen der Netzwerkdaten: {e}")
        return None, None

# Byte-Größe umwandeln
def convert_bytes(size_in_bytes):
    units = [("TB", 1 << 40), ("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)]
    for unit, factor in units:
        if size_in_bytes >= factor:
            return f"{size_in_bytes / factor:.3f}{unit}"
    return f"{size_in_bytes} B"

# Ladebalken berechnen
def update_load_bar(value, thresholds):
    for threshold, char in thresholds:
        if value < threshold:
            return char
    return 0xDB

# Daten aus Datei laden
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as file:
                return json.load(file)
        except Exception as e:
            logging.error(f"Fehler beim Laden der Datei: {e}")
    return {"t_down": 0, "t_up": 0}

# Daten in Datei speichern
def save_data(t_down, t_up):
    try:
        with open(DATA_FILE, "w") as file:
            json.dump({"t_down": t_down, "t_up": t_up}, file)
    except Exception as e:
        logging.error(f"Fehler beim Speichern der Datei: {e}")

# Initialwerte setzen
data = load_data()
t_down, t_up = data["t_down"], data["t_up"]
o_down, o_up = get_network_data()
monat = datetime.now().month

while True:
    if datetime.now().month != monat:
        t_down = t_up = 0
        monat = datetime.now().month
    
    n_down, n_up = get_network_data()
    if n_down is None or n_up is None:
        time.sleep(5)
        continue
    
#    delta_down = (n_down - o_down) if n_down >= o_down else ((1 << 32) - o_down) + n_down
    if n_down >= o_down:
        delta_down = n_down - o_down
        print (f">dd: {delta_down:,}\to: {o_down:,}\tn: {n_down:,}")
    elif n_down < 10000000:
        delta_down = (max - o_down) + n_down
        print (f"<dd: {delta_down:,}\to: {o_down:,}\tn: {n_down:,}")

    t_down = t_down + delta_down

#    delta_up = (n_up - o_up) if n_up >= o_up else ((1 << 32) - o_up) + n_up
    if n_up >= o_up:
        delta_up = n_up - o_up
        print (f">du: {delta_up:,}\to: {o_up:,}\tn: {n_up:,}")
    elif n_up < 10000000:
        delta_up = (max - o_up) + n_up
        print (f"<du: {delta_up:,}\to: {o_up:,}\tn: {n_up:,}")

    t_up = t_up + delta_up

#    t_down += delta_down
#    t_up += delta_up
    
    thresholds_d = [(50_000, 0x5F), (100_000, 0xDC), (100_000_000, 0xFE), (600_000_000, 0xB1)]
    thresholds_u = [(5_000, 0x5F), (10_000, 0xDC), (10_000_000, 0xFE), (60_000_000, 0xB1)]
    
    load_d.append(update_load_bar(delta_down, thresholds_d))
    load_u.append(update_load_bar(delta_up, thresholds_u))
    
    MyVFD.poscur(1, 1)
    MyVFD.write_msg(f"D{convert_bytes(t_down).rjust(10)}")
    MyVFD.poscur(2, 1)
    MyVFD.write_msg(f"U{convert_bytes(t_up).rjust(10)}")
    
    for i in range(8):
        MyVFD.poscur(1, 13 + i)
        MyVFD.printchr(load_d[i])
        MyVFD.poscur(2, 13 + i)
        MyVFD.printchr(load_u[i])
    
    o_down, o_up = n_down, n_up
    
    # Daten speichern
    save_data(t_down, t_up)
    
    time.sleep(5)

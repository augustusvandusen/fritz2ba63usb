from vfdwcn import *
from vfdpos import *
from datetime import datetime


import time
import random
import serial
from fritzconnection import FritzConnection
factory=WincorNixdorfDisplayFactory()
VFDs = factory.get_vfd_wcn()
MyVFD = VFDs[0]
MyVFD.clearscreen()
MyVFD.set_charset(0x30)

# Empfangen: 1,1 Gbit/s
# Senden: 56,7 Mbit/s

# FRITZ!Box Zugangsdaten (ggf. anpassen)
FRITZBOX_IP = ""  # Standard-IP der FRITZ!Box
USERNAME = ""  # Falls kein Benutzer gesetzt ist, leer lassen
PASSWORD = ""  # Hier das FRITZ!Box-Passwort eintragen

# Verbindung zur FRITZ!Box herstellen
fc = FritzConnection(address=FRITZBOX_IP, user=USERNAME, password=PASSWORD)

def get_network_data():
    """Liest die aktuelle Up- und Downloadrate aus der FRITZ!Box."""
    try:
        monitor = fc.call_action("WANCommonInterfaceConfig1", "X_AVM-DE_GetOnlineMonitor",NewSyncGroupIndex=0)
        downstream_bps = list(map(int, monitor['Newds_current_bps'].split(',')))
        upstream_bps = list(map(int, monitor['Newus_current_bps'].split(',')))
    except Exception as e:
        return f"Fehler: {e}", None
    return downstream_bps, upstream_bps

def convert_bytes(size_in_bytes):
        units = [("TB", 1 << 40), ("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)]
        for unit, factor in units:
            if size_in_bytes >= factor:
                return f"{size_in_bytes / factor:.2f} {unit}"
        return f"{size_in_bytes}  B"

def build_bar(values, updown):
    if updown == "d":
        bar_chars = [(0, 0x20), (1_000, 0x5f), (10_000, 0x2e), (100_000, 0xfe), (1_000_000, 0xb0), (10_000_000, 0xb1), (100_000_000, 0xdb)]
    if updown == "u": 
        bar_chars = [(0, 0x20), (1_000, 0x5f), (10_000, 0x2e), (100_000, 0xfe), (1_000_000, 0xb0), (3_000_000, 0xb1), (6_000_000, 0xdb)]
    bar = []
    c = 0
    for  x in values:
        for tresh, code in bar_chars:
            if x >= tresh:
                c = code
        bar.append(c)
    return bar

while True:
    n_down, n_up = get_network_data()
    n_down = n_down[:8]
    n_up = n_up[:8]
    last_d = n_down[0] 
    last_u = n_up[0] 
    print(last_d, last_u)
    d_bar = build_bar(n_down, "d")
    u_bar = build_bar(n_up, "u")
    if last_d:
        MyVFD.poscur(1, 1)
        MyVFD.printchr(0xF2)
        MyVFD.poscur(1, 2)
        MyVFD.write_msg(f"{convert_bytes(last_d).rjust(10)}")
        for i in range(8):
            MyVFD.poscur(1, 13 + i)
            MyVFD.printchr(d_bar[i])
    if last_u:
        MyVFD.poscur(2, 1)
        MyVFD.printchr(0xF3)
        MyVFD.poscur(2, 2)
        MyVFD.write_msg(f"{convert_bytes(last_u).rjust(10)}")
        for i in range(8):
            MyVFD.poscur(2, 13 + i)
            MyVFD.printchr(u_bar[i])
    time.sleep(1)


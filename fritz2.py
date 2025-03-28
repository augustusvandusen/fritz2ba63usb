import argparse
from vfdwcn import WincorNixdorfDisplayFactory
from fritzconnection import FritzConnection
import time

def parse_arguments():
    """Liest die Kommandozeilenargumente."""
    parser = argparse.ArgumentParser(description="Zeigt Netzwerkdaten auf einem VFD an.")
    parser.add_argument("--fritzbox_ip", default="", help="IP-Adresse der FRITZ!Box")
    parser.add_argument("--username", default="", help="Benutzername für die FRITZ!Box")
    parser.add_argument("--password", default="", help="Passwort für die FRITZ!Box")
    return parser.parse_args()

def get_network_data(fc):
    """Liest die aktuelle Up- und Downloadrate aus der FRITZ!Box."""
    try:
        monitor = fc.call_action("WANCommonInterfaceConfig1", "X_AVM-DE_GetOnlineMonitor", NewSyncGroupIndex=0)
        downstream_bps = list(map(int, monitor['Newds_current_bps'].split(',')))[:8]
        upstream_bps = list(map(int, monitor['Newus_current_bps'].split(',')))[:8]
        return downstream_bps, upstream_bps
    except Exception as e:
        print(f"Fehler beim Abrufen der Netzwerkdaten: {e}") #gibt den Fehler in der Konsole aus.
        return None, None

def convert_bytes(size_in_bytes):
    units = [("TB", 1 << 40), ("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)]
    for unit, factor in units:
        if size_in_bytes >= factor:
            return f"{size_in_bytes / factor:.2f} {unit}"
    return f"{size_in_bytes} B"

def build_bar(values, updown):
    bar_chars = {
        "d": [(0, 0x20), (1_000, 0x5f), (10_000, 0x2e), (100_000, 0xfe), (1_000_000, 0xb0), (10_000_000, 0xb1), (100_000_000, 0xdb)],
        "u": [(0, 0x20), (1_000, 0x5f), (10_000, 0x2e), (100_000, 0xfe), (1_000_000, 0xb0), (3_000_000, 0xb1), (6_000_000, 0xdb)]
    }
    bar = [next((code for tresh, code in reversed(bar_chars[updown]) if x >= tresh), 0x20) for x in values]
    return bar

def main():
    args = parse_arguments()

    # Verbindung zur FRITZ!Box herstellen
    try:
        fc = FritzConnection(address=args.fritzbox_ip, user=args.username, password=args.password)
    except Exception as e:
        print(f"Fehler bei der Verbindung zur FRITZ!Box: {e}")
        return

    # VFD initialisieren
    factory = WincorNixdorfDisplayFactory()
    MyVFD = factory.get_vfd_wcn()[0]
    MyVFD.clearscreen()
    MyVFD.set_charset(0x30)

    while True:
        n_down, n_up = get_network_data(fc)

        if n_down and n_up:
            last_d = n_down[0]
            last_u = n_up[0]

            d_bar = build_bar(n_down, "d")
            u_bar = build_bar(n_up, "u")

            MyVFD.poscur(1, 1)
            MyVFD.printchr(0xF2)
            MyVFD.poscur(1, 2)
            MyVFD.write_msg(f"{convert_bytes(last_d).rjust(10)}")
            for i, char_code in enumerate(d_bar):
                MyVFD.poscur(1, 13 + i)
                MyVFD.printchr(char_code)

            MyVFD.poscur(2, 1)
            MyVFD.printchr(0xF3)
            MyVFD.poscur(2, 2)
            MyVFD.write_msg(f"{convert_bytes(last_u).rjust(10)}")
            for i, char_code in enumerate(u_bar):
                MyVFD.poscur(2, 13 + i)
                MyVFD.printchr(char_code)

        time.sleep(1)

if __name__ == "__main__":
    main()
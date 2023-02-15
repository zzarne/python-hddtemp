#!/usr/bin/python3

import os
import glob

import argparse
import dbus
import socketserver


class Properties:
    def __init__(self, props, interface):
        self.props = props
        self.interface = interface
        self.cache = None

    def get(self, name, default=None, cached=True):
        if self.cache is None or not cached:
            cache = self.props.GetAll(self.interface)
        return cache.get(name, default)


class Hdd:
    def __init__(self, drive, ata, props):
        self.drive = drive  # unused
        self.ata = ata
        self.props = props
        self.drive_props = Properties(props, "org.freedesktop.UDisks2.Drive")
        self.ata_props = Properties(props, "org.freedesktop.UDisks2.Drive.Ata")
        self.vendor = self.drive_props.get("Vendor")
        self.model = self.drive_props.get("Model")
        self.serial = self.drive_props.get("Serial")
        self.wwn = self.drive_props.get("WWN")
        self.uid = "_".join([x for x in (self.vendor, self.model, self.serial) if x])
        self.uid = self.uid.replace(" ", "_")
        self.path = "/dev/disk/by-id/wwn-" + self.wwn
        self.dev = os.path.realpath(self.path)
        self.name = os.path.split(self.dev)[1]
        temp = glob.glob(f"/sys/class/block/{self.name}/device/hwmon/hwmon*/temp1_input")
        self.hwmon = temp[0] if len(temp) == 1 else None
        self.unit = "C"

    def is_idle(self):
        try:
            raw = self.ata.PmGetState({})
            return raw == 0x00
        except dbus.exceptions.DBusException:
            return None

    def get_ata_temperature(self):
        return round(self.ata_props.get("SmartTemperature", cached=False) - 273.15, 2) # kelvin

    def get_hwmon_temperature(self):
        if not os.path.exists(self.hwmon):
            return None
        return round(int(open(self.hwmon, "r", encoding="ascii").read().strip()) / 1000, 2)

    def get_temperature(self):
        temp = self.get_hwmon_temperature()
        if temp is not None:
            return temp
        return self.get_ata_temperature()

    def report(self):
        idle = self.is_idle()
        data = (
                "",
                self.dev,
                self.model,
                str(int(round(self.get_temperature()))) if not idle else "SLP",
                self.unit if not idle else "*",
                "",
                )
        return args.separator.join(data)


    def dump(infos):
        for info, detail in infos.items():
            sig = None
            try:
                sig = detail.signature
            except AttributeError:
                pass
            if sig == "y":
                data = detail
                try:
                    data = bytearray(data).replace(b'\x00', b'').decode()
                except:
                    pass
                print(f"  {info}:  {data}")
            elif sig == "ay":
                print(f"  {info}: -- {sig}")
            elif sig is None:
                print(f"  {info}: {detail}")
            else:
                print(f"  {info}: {detail}")

    def scan():
        drives = []
        bus = dbus.SystemBus()
        obj = bus.get_object("org.freedesktop.UDisks2", "/org/freedesktop/UDisks2")
        manager = dbus.Interface(obj, 'org.freedesktop.DBus.ObjectManager')
        for fs_obj, v in manager.GetManagedObjects().items():
            if args.debug:
                print(f"object: {fs_obj}")
                print(f"interfaces: {v.keys()}")
                Hdd.dump(v.get('org.freedesktop.UDisks2.Block', {}))
            ata_info = v.get('org.freedesktop.UDisks2.Drive.Ata')
            if not ata_info:
                continue
            drive_info = v.get('org.freedesktop.UDisks2.Drive')
            if not drive_info:
                continue
            if args.debug:
                Hdd.dump(ata_info)
                Hdd.dump(drive_info)
                print()
            udisks2 = bus.get_object("org.freedesktop.UDisks2", fs_obj)
            drive = dbus.Interface(udisks2, "org.freedesktop.UDisks2.Drive")
            ata = dbus.Interface(udisks2, "org.freedesktop.UDisks2.Drive.Ata")
            props = dbus.Interface(udisks2, dbus.PROPERTIES_IFACE)
            drives.append(Hdd(drive, ata, props))
        return drives


class HddTempHandler(socketserver.BaseRequestHandler):
    def handle(self):
        # "|/dev/sda|WDC WD40EZRX-00SPEB0|34|C||/dev/sdc|WDC WD60EFRX-68L0BN1|SLP|*||/dev/sdd|WDC WD20EARX-00PASB0|33|C||/dev/sde|WDC WD60EFRX-68L0BN1|32|C||/dev/sdf|WDC WD30EZRX-00SPEB0|32|C|"
        data = [x.report() for x in DRIVES]
        data = "".join(data)

        self.request.sendall(data.encode())


def parse_args():
    parser = argparse.ArgumentParser(description='hddtemp partially reimplemented in python',
            epilog="Can use any of udisks2 daemon and drivetemp kernel module to get the drives' temperatures. Will report whether disks are spun down if run as root.")

    parser.add_argument('-D', '--debug', action='store_true',
            help="Display various UDisks2 fields and their values.")

    parser.add_argument('-d', '--daemon', action='store_true',
            help="Execute hddtemp in TCP/IP daemon mode (port 7634 by default). Always runs in foreground")

    parser.add_argument('-p', '--port', type=int, default=7634,
            help="Port number to listen to (in TCP/IP daemon mode).")

    parser.add_argument('-l', '--listen', type=str, default="localhost",
            help="Listen on a specific address. Argument is a string containing a host name or a numeric host address string. The numeric host address string is a dotted-decimal IPv4 address or an IPv6 hex address.")

    parser.add_argument('-s', '--separator', type=str, default='|',
            help="Separator to use between fields (in TCP/IP daemon mode). The default separator is '|'.")

    args = parser.parse_args()

    return args


if __name__ == "__main__":
    args = parse_args()
    DRIVES = Hdd.scan()
    DRIVES.sort(key=lambda x: x.name)
    if args.daemon:
        print(f"listening on {args.listen}:{args.port}")
        with socketserver.TCPServer((args.listen, args.port), HddTempHandler) as server:
            print(f'monitoring {", ".join([x.name for x in DRIVES])}')
            server.serve_forever()

    for drive in DRIVES:
        print(f"{drive.name}: {drive.get_temperature()} °{drive.unit} {drive.is_idle()=}")

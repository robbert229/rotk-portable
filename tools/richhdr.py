#!/usr/bin/env python3
"""Report Microsoft linker Rich records from PE files."""
import argparse
import json
from pathlib import Path
import struct

# Product names and release families cross-checked against:
# https://gist.github.com/skochinsky/07c8e95e33d9429d81a75622b5d24c8b
# https://github.com/dishather/richprint/blob/master/comp_id.txt
PRODUCTS = {
    0: ("Unknown", "Unmarked (old)"),
    1: ("Import0", "Unmarked"),
    4: ("Linker600", "Visual C++ 6.0"),
    6: ("Cvtres500", "CVTRES 5.00"),
    10: ("Utc12_C", "Visual C++ 6.0"),
    11: ("Utc12_CPP", "Visual C++ 6.0"),
    12: ("AliasObj60", "Visual C++ 6.0"),
    14: ("Masm613", "MASM 6.13"),
    18: ("Masm614", "MASM 6.14"),
    19: ("Linker512", "Linker 5.12"),
    25: ("Implib700", "Visual Studio .NET 2002-era"),
    28: ("Utc13_C", "Visual Studio .NET 2002-era"),
    29: ("Utc13_CPP", "Visual Studio .NET 2002-era"),
    37: ("Linker620", "Linker 6.20"),
    39: ("AliasObj70", "Visual Studio .NET 2002-era"),
    48: ("Utc12_2_C", "Visual C++ 6.0 Processor Pack"),
    49: ("Utc12_2_CPP", "Visual C++ 6.0 Processor Pack"),
    61: ("Linker700", "Visual Studio .NET 2002-era"),
    63: ("Export700", "Visual Studio .NET 2002-era"),
    64: ("Masm700", "Visual Studio .NET 2002-era"),
    69: ("Cvtres700", "Visual Studio .NET 2002-era"),
    93: ("Implib710", "Visual Studio .NET 2003 family"),
    95: ("Utc1310_C", "Visual Studio .NET 2003 family"),
}
VERSIONS = {
    (6, 1668): "Visual Studio 97 SP3",
    (10, 8966): "Visual C++ 6.0 SP5",
    (11, 8799): "Visual C++ 6.0 SP4",
    (11, 8966): "Visual C++ 6.0 SP5",
    (25, 9210): "Visual Studio .NET 2002-era import library",
    (28, 9178): "Windows XP SP1 DDK (VC 13.00)",
    (29, 9178): "Windows XP SP1 DDK (VC 13.00)",
}
VS2002_RTM_PRODUCTS = {28, 29, 61, 63, 64, 69}
MASK = 0xffffffff
DANS = 0x536e6144


def rol(value, count):
    count %= 32
    return ((value << count) | (value >> (32 - count))) & MASK


def decode(data):
    """Return offsets and decoded records for one PE image."""
    if len(data) < 64 or data[:2] != b"MZ":
        raise ValueError("missing DOS header")
    pe, = struct.unpack_from("<I", data, 0x3c)
    if pe < 64 or data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("missing PE signature")
    result = {"pe_offset": pe, "status": "absent", "entries": []}
    for rich in range((pe - 8) & ~3, 63, -4):
        if data[rich:rich + 4] != b"Rich":
            continue
        result.update(status="malformed", rich_offset=rich)
        key, = struct.unpack_from("<I", data, rich + 4)
        marker = struct.pack("<4I", DANS ^ key, key, key, key)
        for dans in range(rich - 16, 63, -8):
            if data[dans:dans + 16] != marker:
                continue
            decoded = [(comp ^ key, count ^ key) for comp, count in
                       struct.iter_unpack("<II", data[dans + 16:rich])]
            stub = data[:0x3c] + bytes(4) + data[0x40:dans]
            record_checksum = (dans + sum(rol(comp, count) for comp, count in decoded)) & MASK
            checksum = (record_checksum
                        + sum(rol(byte, offset) for offset, byte in enumerate(stub))) & MASK
            if checksum != key and record_checksum == key:
                result["record_only_checksum"] = record_checksum
            return dict(result, dans_offset=dans, key=key, checksum=checksum,
                        status="valid" if checksum == key else "invalid",
                        entries=[entry(comp, count) for comp, count in decoded])
    return result


def entry(comp, count):
    prodid, build = comp >> 16, comp & 0xffff
    name, family = PRODUCTS.get(prodid, ("Unknown", "Unknown"))
    version = VERSIONS.get((prodid, build), family)
    if build == 9466 and prodid in VS2002_RTM_PRODUCTS:
        version = "Visual Studio .NET 2002 RTM"
    return dict(prodid=prodid, name=name, build=build, count=count, version=version)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit a JSON array")
    parser.add_argument("files", nargs="+", type=Path, metavar="PE")
    args = parser.parse_args()
    reports = []
    for path in args.files:
        try:
            report = decode(path.read_bytes())
        except (OSError, ValueError) as exc:
            report = {"status": "error", "error": str(exc), "entries": []}
        reports.append(dict(report, file=str(path)))

    if args.json:
        print(json.dumps(reports, indent=2))
    else:
        for report in reports:
            print(f"{report['file']}: Rich {report['status']}")
            for field in ("pe_offset", "dans_offset", "rich_offset", "key", "checksum",
                          "record_only_checksum"):
                if field in report:
                    print(f"  {field} = 0x{report[field]:08x}")
            if "error" in report:
                print(f"  {report['error']}")
            for row in report["entries"]:
                print("  {prodid:4d} {name:16s} {build:5d} {count:5d} {version}".format(**row))
    return int(any(report["status"] == "error" for report in reports))


if __name__ == "__main__":
    raise SystemExit(main())

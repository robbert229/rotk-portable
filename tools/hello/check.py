"""Verify the compiler and linker IDs recorded in the smoke-test PE."""
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import richhdr

def compiler_id(path):
    data = path.read_bytes()
    symbols, count = struct.unpack_from("<II", data, 8)
    if symbols < 20 or symbols + 18 * count > len(data):
        raise ValueError(f"{path}: invalid COFF symbol table")
    index = 0
    while index < count:
        offset = symbols + 18 * index
        name, value, section, _, _, auxiliary = struct.unpack_from("<8sIhHBB", data, offset)
        if name == b"@comp.id" and section == -1:
            return value
        index += 1 + auxiliary
    raise ValueError(f"{path}: no absolute @comp.id symbol")


obj = Path(sys.argv[1])
product = richhdr.entry(compiler_id(obj), 1)
if (product["prodid"], product["build"]) != (28, 9466):
    raise SystemExit(f"{obj}: unexpected @comp.id {product}")
print(f"{obj}: @comp.id prodid 28 (Utc13_C), build 9466")

path = Path(sys.argv[2])
report = richhdr.decode(path.read_bytes())
entries = {(row["prodid"], row["build"]) for row in report["entries"]}
if report["status"] != "valid" or not {(28, 9466), (61, 9466)} <= entries:
    raise SystemExit(f"{path}: expected valid Rich records for Utc13_C and Linker700 build 9466")
print(f"{path}: Rich valid, prodid 28 (Utc13_C) and 61 (Linker700), build 9466")

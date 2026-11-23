"""Synthetic PE metadata checks and an optional retail catalogue reproduction."""

import csv
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from uuid import UUID

from tools import pecat

REPO = Path(__file__).resolve().parents[1]
GAME = Path(os.environ.get("ROTK_GAME_DIR") or pecat.DEFAULT_GAME_DIR)
ROTK_SHA256 = "95af128c93c63fe5d847609b45f3ba146af56f01c76215389bd1aabf0eb2a5a2"
GUID = UUID("10203040-5060-7080-90ab-cdef01234567")


def pad(data):
    return data + bytes(-len(data) % 4)


def version_block(key, kind, value=b"", children=b""):
    body = pad(bytes(6) + (key + "\0").encode("utf-16le")) + value
    if children:
        body = pad(body) + children
    return struct.pack("<HHH", len(body), len(value) // (2 if kind else 1), kind) + body[6:]


def fixture(*, pe32):
    data = bytearray(0x600)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3c, 0x80)
    optional = 0x98
    optional_size, directory_start = (0xe0, 96) if pe32 else (0xf0, 112)
    struct.pack_into("<4sHHIIIHH", data, 0x80, b"PE\0\0",
                     0x14c if pe32 else 0x8664, 1, 1, 0, 0, optional_size, 0x102)
    base = 0x400000 if pe32 else 0x140000000
    struct.pack_into("<HBB", data, optional, 0x10b if pe32 else 0x20b, 7, 1)
    struct.pack_into("<I", data, optional + 16, 0x1000)
    struct.pack_into("<I" if pe32 else "<Q", data, optional + (28 if pe32 else 24), base)
    struct.pack_into("<II6H4IHH", data, optional + 32, 0x1000, 0x200,
                     4, 0, 0, 0, 5, 2, 0, 0x2000, 0x200, 0x12345678, 3, 0x8140)
    struct.pack_into("<I", data, optional + directory_start - 4, 16)
    struct.pack_into("<8s4I12xI", data, optional + optional_size,
                     b".a \x01\\", 0x400, 0x1000, 0x400, 0x200, 0x60000020)

    def rva(offset):
        return offset + 0xe00

    for index, offset, length in ((0, 0x380, 40), (1, 0x200, 40), (2, 0x3c0, 88),
                                  (6, 0x2c0, 56), (9, 0x550, 40), (13, 0x230, 64)):
        struct.pack_into("<II", data, optional + directory_start + index * 8,
                         rva(offset), length)

    struct.pack_into("<5I", data, 0x200, 0, 0, 0, rva(0x290), rva(0x270))
    # PE32 uses a legacy VA-based delay descriptor. PE32+ uses RVAs.
    displacement = base if pe32 else 0
    delay_lookup = 0x280 if pe32 else 0x270
    struct.pack_into("<8I", data, 0x230, int(not pe32), rva(0x2a0) + displacement,
                     0, rva(0x270) + displacement, rva(delay_lookup) + displacement, 0, 0, 0)
    struct.pack_into("<III" if pe32 else "<QQQ", data, 0x270,
                     rva(0x2b0), (1 << (31 if pe32 else 63)) | 42, 0)
    if pe32:
        struct.pack_into("<III", data, delay_lookup, rva(0x2b0) + base, 0x8000002a, 0)
    data[0x290:0x299] = b"Demo.dll\0"
    data[0x2a0:0x2aa] = b"Delay.dll\0"
    data[0x2b2:0x2b8] = b"Hello\0"
    struct.pack_into("<III", data, 0x38c, rva(0x290), 1, 3)

    rsds = b"RSDS" + GUID.bytes_le + struct.pack("<I", 3) + b"build;new.pdb\0"
    nb10 = struct.pack("<4sIII", b"NB10", 0, 0x12345678, 7) + b"old.pdb\0"
    data[0x300:0x300 + len(rsds)] = rsds
    data.extend(nb10 + b"\xff")
    struct.pack_into("<4I", data, 0x2cc, 2, len(rsds), rva(0x300), 0)
    struct.pack_into("<4I", data, 0x2e8, 2, len(nb10), 0, 0x600)

    value = ("Demo; Company\0").encode("utf-16le")
    company = version_block("CompanyName", 1, value)
    table = version_block("040904b0", 1, children=company)
    info = version_block("StringFileInfo", 1, children=table)
    version = version_block("VS_VERSION_INFO", 0, bytes(52), info)
    data[0x440:0x440 + len(version)] = version
    for relative, name, target in ((0, 16, 0x80000018), (24, 1, 0x80000030), (48, 1033, 72)):
        struct.pack_into("<HII", data, 0x3c0 + relative + 14, 1, name, target)
    struct.pack_into("<II", data, 0x408, rva(0x440), len(version))
    return bytes(data)


def run_catalogue(game, output):
    return subprocess.run(
        [sys.executable, "-I", str(REPO / "tools/pecat.py"), "--output-dir", str(output)],
        env={**os.environ, "ROTK_GAME_DIR": str(game)}, cwd=output.parent,
        capture_output=True, text=True,
    )


def csv_rows(path):
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


class PECatalogueTest(unittest.TestCase):
    def test_synthetic_pe32_and_pe32_plus(self):
        for pe32 in (True, False):
            with self.subTest(pe32=pe32):
                data = fixture(pe32=pe32)
                row, sections, imports = pecat.catalogue("Demo.bin", data)
                self.assertEqual(row["machine"], "0x14c" if pe32 else "0x8664")
                self.assertEqual(row["image_base"], "0x400000" if pe32 else "0x140000000")
                self.assertEqual(row["timestamp_utc"], "1970-01-01T00:00:01Z")
                self.assertEqual(row["linker_version"], "7.01")
                self.assertEqual(row["os_version"], "4.0")
                self.assertEqual(row["subsystem_version"], "5.2")
                self.assertEqual(row["subsystem"], 3)
                self.assertEqual(row["dll_characteristics"], "0x8140")
                self.assertEqual(row["section_count"], 1)
                self.assertEqual(row["entry_section"], r".a\x20\x01\x5c")
                self.assertEqual(sections[0][2:8],
                                 (row["entry_section"], "0x1000", "0x400",
                                  "0x200", "0x400", "0x60000020"))
                self.assertEqual(row["checksum_stored"], "0x12345678")
                self.assertEqual(row["checksum_computed"], "0x1b62" if pe32 else "0x4f62")
                self.assertEqual(row["overlay_size"], 25)
                self.assertEqual(row["tls_present"], 1)
                self.assertEqual(row["rich_status"], "absent")
                self.assertEqual(row["resource_types"], "16=1")
                self.assertEqual(row["CompanyName"], "Demo%3B Company")
                self.assertEqual(row["codeview_format"], "RSDS;NB10")
                self.assertEqual(row["pdb_path"], "build%3Bnew.pdb;old.pdb")
                self.assertEqual(row["pdb_guid"], f"{GUID};")
                self.assertEqual(row["pdb_age"], "3;7")
                self.assertEqual(row["pdb_timestamp"], ";0x12345678")
                self.assertEqual(row["debug_directory"], "2@0x300/38;2@0x600/24")
                self.assertEqual((row["export_dll_name"], row["export_count"]), ("Demo.dll", 3))
                self.assertEqual(row["import_function_counts"], "2")
                self.assertEqual(row["delay_import_function_counts"], "2")
                self.assertEqual([entry[1:4] for entry in imports], [
                    ("Demo.dll", "Hello", "regular"), ("Demo.dll", "#42", "regular"),
                    ("Delay.dll", "Hello", "delay"), ("Delay.dll", "#42", "delay"),
                ])

    def test_checksum_odd_file_and_unaligned_checksum_field(self):
        self.assertEqual(pecat.checksum(bytes.fromhex("ffff12345678ffff03"), 2), 12)
        self.assertEqual(pecat.checksum(bytes.fromhex("01123456780203"), 1), 523)

    def test_cli_discovers_by_signature_and_guards_game_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            game = root / "game install"
            (game / "Support").mkdir(parents=True)
            (game / "Support/z.bin").write_bytes(fixture(pe32=False))
            (game / "A.exe").write_bytes(fixture(pe32=True))
            (game / "other.dll").write_bytes(b"MZ" + bytes(90))
            output = root / "catalogue"
            result = run_catalogue(game, output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual([row["path"] for row in csv_rows(output / "binaries.csv")],
                             ["A.exe", "Support/z.bin"])
            result = run_catalogue(game, game / "new")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("inside the game prefix", result.stderr)
            self.assertFalse((game / "new").exists())

    @unittest.skipUnless(GAME.is_dir(), "game directory is absent")
    def test_retail_regeneration(self):
        corpus = REPO / "re/corpus"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "pecat"
            result = run_catalogue(GAME.resolve(), output)
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in ("binaries.csv", "pe_sections.csv", "pe_imports.csv"):
                self.assertEqual((output / name).read_bytes(), (corpus / name).read_bytes(), name)

        expected = {}
        for row in csv_rows(corpus / "manifest.csv"):
            if row["origin"] != "install":
                continue
            with (GAME / row["path"]).open("rb") as source:
                header = source.read(64)
                if len(header) == 64 and header[:2] == b"MZ":
                    source.seek(int.from_bytes(header[60:64], "little"))
                    if source.read(4) == b"PE\0\0":
                        expected[row["path"]] = (row["sha256"], row["size"])
        actual = {row["path"]: row for row in csv_rows(corpus / "binaries.csv")}
        self.assertEqual({path: (row["sha256"], row["size"]) for path, row in actual.items()},
                         expected)
        rotk = actual["ROTK.exe"]
        self.assertEqual(rotk["sha256"], ROTK_SHA256)
        self.assertEqual(rotk["section_count"], "8")
        self.assertEqual(rotk["entry_section"], "stxt371")
        self.assertEqual(rotk["rich_status"], "valid")

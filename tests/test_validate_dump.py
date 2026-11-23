"""Exercise the validator under isolated Python with synthetic and local PEs."""

import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

TOOL = Path(__file__).resolve().parents[1] / "tools/validate_dump.py"
GAME = Path(os.environ.get("ROTK_GAME_DIR") or Path.home() /
            "Games/lord-of-the-rings-the-return-of-the-king/drive_c/"
            "Program Files (x86)/EA GAMES/LOTR The Return of the King tm")
OPTIONAL = 0x98
TABLE = OPTIONAL + 224


def fixture():
    data = bytearray(2_874_232)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3c, 0x80)
    struct.pack_into("<4sHHIIIHH", data, 0x80, b"PE\0\0", 0x14c, 5, 0, 0, 0, 224, 2)
    struct.pack_into("<H", data, OPTIONAL, 0x10b)
    struct.pack_into("<I", data, OPTIONAL + 16, 0x1000)
    struct.pack_into("<III", data, OPTIONAL + 28, 0x400000, 0x1000, 0x200)
    struct.pack_into("<II", data, OPTIONAL + 56, 0x6000, 0x400)
    struct.pack_into("<I", data, OPTIONAL + 92, 16)
    struct.pack_into("<II", data, OPTIONAL + 104, 0x2000, 160)
    for index, name in enumerate((b".text", b".idata", b"stxt371", b"stxt774", b"        ")):
        struct.pack_into("<8s4I", data, TABLE + index * 40, name, 0x200,
                         (index + 1) * 0x1000, 0x200, 0x400 + index * 0x200)
    for index, name in enumerate((b"D3D8", b"DInput8", b"DSound", b"EAX",
                                  b"DivxMediaLib", b"Kernel32", b"User32")):
        name_offset = 0xa0 + 20 * index
        thunk = 0x2140 + 8 * index
        struct.pack_into("<5I", data, 0x600 + 20 * index,
                         0, 0, 0, 0x2000 + name_offset, thunk)
        dll = name + b".dll\0"
        data[0x600 + name_offset:0x600 + name_offset + len(dll)] = dll
        struct.pack_into("<I", data, 0x740 + 8 * index, 0x80000001)
    return data


def run(path, *options):
    result = subprocess.run([sys.executable, "-I", str(TOOL), *options, str(path)],
                            check=False, capture_output=True, text=True)
    return result.returncode, json.loads(result.stdout)


class ValidatorTests(unittest.TestCase):
    def validate(self, data, *options):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.exe"
            path.write_bytes(data)
            return run(path, *options)

    def test_pass_and_stable_report(self):
        status, report = self.validate(fixture())
        self.assertEqual(status, 0)
        self.assertTrue(report["ok"])
        self.assertEqual(list(report["checks"]), sorted(report["checks"]))

    def test_structural_failure(self):
        for offset, value in ((0, 0), (0x80, 0), (OPTIONAL + 56, 0x5000),
                              (TABLE + 20, 0xffffff00), (TABLE + 60, 0x400)):
            with self.subTest(offset=offset):
                data = fixture()
                struct.pack_into("<I", data, offset, value)
                status, report = self.validate(data, "--structural")
                self.assertEqual(status, 1)
                self.assertFalse(report["checks"]["pe"]["ok"])
        self.assertEqual(self.validate(fixture()[:TABLE + 20])[0], 1)

    def test_rotk_failures(self):
        for check, offset, value in (
                ("x86", 0x84, b"\x64\x86"),
                ("entry_in_text", OPTIONAL + 16, struct.pack("<I", 0x3000)),
                ("text_entropy", 0x400, bytes(range(256)) * 2),
                ("imports", 0x6a0, b"fake"),
                ("imports", 0x60c, struct.pack("<I", 0x6000)),
                ("file_size", 0xe00, b"")):
            with self.subTest(check=check, offset=offset):
                data = fixture()
                if value:
                    data[offset:offset + len(value)] = value
                else:
                    del data[offset:]
                status, report = self.validate(data)
                self.assertEqual(status, 1)
                self.assertFalse(report["checks"][check]["ok"])
                self.assertEqual(self.validate(data, "--structural")[0], 0)

    def test_residual_branch_counts(self):
        data = fixture()
        struct.pack_into("<BiBi", data, 0x400, 0xe8, 0x3000 - 0x1005,
                         0xe9, 0x4000 - 0x100a)
        struct.pack_into("<2sI2sI2sI", data, 0x40a, b"\xff\x15", 0x402140,
                         b"\xff\x25", 0x402140, b"\xff\x15", 0x402144)
        struct.pack_into("<I", data, 0x740, 0x405000)
        status, report = self.validate(data)
        self.assertEqual(status, 0)
        self.assertEqual(report["checks"]["stub_references"],
                         {"ok": True, "rel32": 2, "iat_indirect": 2, "total": 4})

    @unittest.skipUnless(GAME.is_dir(), "retail game directory unavailable")
    def test_retail_packed(self):
        status, report = run(GAME / "ROTK.exe")
        self.assertEqual(status, 1)
        for check in ("entry_in_text", "text_entropy", "imports"):
            self.assertFalse(report["checks"][check]["ok"])

    @unittest.skipUnless(GAME.is_dir(), "retail game directory unavailable")
    def test_retail_uninstaller(self):
        status, report = run(GAME / "eauninstall.exe", "--structural")
        self.assertEqual(status, 0)
        self.assertEqual(set(report["checks"]), {"pe"})

"""Rich header decoder and installed-image regression checks."""
import os
from pathlib import Path
import struct
import unittest

from tools import richhdr


GAME = Path(os.environ.get("ROTK_GAME_DIR") or Path.home() / (
    "Games/lord-of-the-rings-the-return-of-the-king/drive_c/Program Files (x86)/"
    "EA GAMES/LOTR The Return of the King tm"
))

RETAIL = {
    "ROTK.exe": (0x2f195187, [
        (25, 9210, 9), (11, 8799, 1), (39, 9162, 3), (28, 9178, 4),
        (1, 0, 156), (18, 8444, 1), (29, 9178, 12), (0, 0, 8),
        (29, 9466, 10), (64, 9466, 43), (28, 9466, 563),
        (63, 9466, 1), (69, 9466, 1), (61, 9466, 1),
    ]),
    "eauninstall.exe": (0x1641cd22, [
        (39, 9162, 3), (37, 8755, 2), (28, 9178, 8), (64, 9466, 29),
        (28, 9466, 186), (25, 9210, 23), (1, 0, 569), (29, 9466, 113),
        (69, 9466, 1), (61, 9466, 1),
    ]),
    "rotk_uninst.exe": (0xa99a74a6, [
        (37, 8755, 2), (28, 9178, 7), (25, 9210, 21), (1, 0, 531),
        (64, 9466, 27), (28, 9466, 140), (29, 9466, 95),
        (69, 9466, 1), (61, 9466, 1),
    ]),
}


class RichHeaderTest(unittest.TestCase):
    def test_synthetic_pe(self):
        blob = bytearray(0xb4)
        blob[:2] = b"MZ"
        struct.pack_into("<I", blob, 0x3c, 0xb0)
        # DanS offset + 'M' + rol('Z', 1) + rol(0x1c24fa, 2).
        key = 0x709569
        struct.pack_into("<6I", blob, 0x80, 0x536e6144 ^ key, key, key, key,
                         0x1c24fa ^ key, 2 ^ key)
        struct.pack_into("<4sI", blob, 0x98, b"Rich", key)
        blob[0xb0:] = b"PE\0\0"
        report = richhdr.decode(blob)
        self.assertEqual(report["status"], "valid")
        self.assertEqual(report["dans_offset"], 0x80)
        self.assertEqual(report["rich_offset"], 0x98)
        self.assertEqual(report["entries"], [
            dict(prodid=28, name="Utc13_C", build=9466, count=2,
                 version="Visual Studio .NET 2002 RTM"),
        ])

        blob[0x40] = 1
        report = richhdr.decode(blob)
        self.assertEqual(report["status"], "invalid")
        self.assertEqual(report["checksum"], key + 1)
        blob[0x80] ^= 1
        self.assertEqual(richhdr.decode(blob)["status"], "malformed")
        blob[0x98] = 0
        self.assertEqual(richhdr.decode(blob)["status"], "absent")

    @unittest.skipUnless(GAME.is_dir(), "game directory is absent")
    def test_retail_pe(self):
        for name, (key, entries) in RETAIL.items():
            with self.subTest(binary=name):
                report = richhdr.decode((GAME / name).read_bytes())
                self.assertEqual(report["status"], "valid")
                self.assertEqual(report["key"], key)
                self.assertEqual([
                    (row["prodid"], row["build"], row["count"]) for row in report["entries"]
                ], entries)

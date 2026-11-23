"""File-reference extraction and retail CSV regeneration."""

import csv
from hashlib import sha256
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from tools import filerefs


ROOT = Path(__file__).resolve().parents[1]
CLI = [sys.executable, "-I", str(ROOT / "tools/filerefs.py")]
CSV_NAMES = ("filerefs.csv", "listed_files.csv")


def pe(payload):
    data = bytearray(0x200)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", data, 0x86, 1)
    struct.pack_into("<H", data, 0x94, 0xE0)
    struct.pack_into("<H", data, 0x98, 0x10B)
    struct.pack_into("<I", data, 0x98 + 60, 0x200)
    struct.pack_into("<8s4I", data, 0x178, b".rdata", len(payload),
                     0x1000, len(payload), 0x200)
    return bytes(data) + payload


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


class FileRefsTest(unittest.TestCase):
    def test_scan_offsets_and_encodings(self):
        raw = r"Data\Game\Scene.SCw"
        wide = "dir/unlisted.xyz"
        for padding in (b"", b"\xff"):
            prefix = raw.encode() + b"\0\xff" + padding
            data = (prefix + wide.encode("utf-16le") + b"\0\0\xff"
                    + b"=%s.scw\0text from a diagnostic\0junk/??\0unterminated.avi")
            with self.subTest(padding=padding):
                self.assertCountEqual(
                    filerefs.binary_strings(data, filerefs.EXTENSIONS, {}),
                    [
                        (0, "ascii", raw, "literal"),
                        (len(prefix), "utf-16le", wide, "literal"),
                        (len(prefix) + len(wide) * 2 + 4, "ascii", "%s.scw", "pattern"),
                    ],
                )

    def test_cli_cross_references(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch) / "retail install"
            root.mkdir()
            output = Path(scratch) / "output"
            (root / "ROTK.exe").write_bytes(pe(
                b"Game\\One.SCw\0%s.scw\0DiscOnly.PAC\0Data/Game/\0"
                b"Support\\*.*\0Data/Game/shot%02d.avi\0Data/Game/%s\0"
            ))
            (root / "helper.dll").write_bytes(pe(b"other.dll\0"))
            (root / "Data/Game").mkdir(parents=True)
            (root / "Data/Game/One.scw").touch()
            (root / "Data/Game/shot07.avi").touch()
            (root / "Support").mkdir()
            (root / "Support/noextension").touch()
            (root / "filelist.txt").write_text(
                "1,1,Support\\*.* \n2,5,DiscOnly.PAC,123\n", encoding="ascii"
            )
            (root / "common_filelist.txt").write_text("1,1,helper.dll\n", encoding="ascii")
            (root / "manifest.txt").write_text(
                "\nData\\Game\\One.scw\nData/Game/shot07.avi\n", encoding="ascii"
            )
            (root / "Input.ini").write_text(
                '; ignored.avi\n[controls]\nkey = CTRL\nvideo = "Data/Game/shot07.avi"\n',
                encoding="ascii",
            )
            command = CLI + ["--game-dir", str(root), "--output-dir"]
            subprocess.run(command + [str(output)], check=True)
            refs = {row["string"]: row for row in read_csv(output / "filerefs.csv")}
            scene = refs[r"Game\One.SCw"]
            self.assertEqual((scene["source"], scene["offset"], scene["section"]),
                             ("ROTK.exe", "0x00000200", ".rdata"))
            self.assertEqual(scene["resolves_to"], "Data/Game/One.scw")
            self.assertEqual(refs["%s.scw"]["status"], "pattern-matches-1")
            self.assertEqual(refs["Data/Game/shot%02d.avi"]["resolves_to"], "Data/Game/shot07.avi")
            self.assertEqual(refs["Data/Game/%s"]["status"], "pattern-matches-2")
            self.assertEqual(refs["DiscOnly.PAC"]["resolves_to"], "listed:disconly.pac")
            self.assertEqual(refs["DiscOnly.PAC"]["status"], "missing")
            self.assertEqual(refs["Data/Game/"]["kind"], "directory")
            self.assertEqual(refs[r"Support\*.*"]["resolves_to"], "Support/noextension")
            self.assertEqual(refs["other.dll"]["source"], "helper.dll")

            listed = read_csv(output / "listed_files.csv")
            self.assertEqual([(row["source"], row["line"], row["present_in_install"])
                              for row in listed], [
                ("Input.ini", "4", "yes"),
                ("common_filelist.txt", "1", "yes"),
                ("filelist.txt", "1", "yes"),
                ("filelist.txt", "2", "no"),
                ("manifest.txt", "2", "yes"),
                ("manifest.txt", "3", "yes"),
            ])
            self.assertEqual((listed[3]["type"], listed[3]["size_if_given"]), ("5", "123"))

            result = subprocess.run(command + [str(root)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"outside the retail install", result.stderr)
            self.assertFalse((root / "filerefs.csv").exists())

            dump = Path(scratch) / "unpacked.exe"
            dump.write_bytes(pe(b"NewFile.scw\0"))
            subprocess.run(command + [str(output), "--exe", str(dump)], check=True)
            self.assertEqual([row["source"] for row in read_csv(output / "filerefs.csv")],
                             ["helper.dll", "unpacked.exe"])

    def test_retail_regeneration(self):
        game = filerefs.game_dir()
        if not (game / "ROTK.exe").is_file():
            self.skipTest("retail game directory is absent")
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch)
            command = CLI + ["--game-dir", str(game), "--output-dir", str(output)]
            subprocess.run(command, check=True)
            first = [(output / name).read_bytes() for name in CSV_NAMES]
            subprocess.run(command, check=True)
            self.assertEqual(first, [(output / name).read_bytes() for name in CSV_NAMES])

            # Check the committed retail baseline when the install file set
            # and content hashes match the corpus inputs for this report.
            baseline = {row["path"]: row["sha256"]
                        for row in read_csv(ROOT / "re/corpus/manifest.csv")
                        if row["origin"] == "install"}
            files, _ = filerefs.install_index(game)
            paths = {path for matches in files.values() for path in matches}
            if paths == baseline.keys() and all(
                sha256((game / path).read_bytes()).hexdigest() == baseline[path]
                for path in paths if path.lower().endswith((".exe", ".dll"))
                or Path(path).name.lower() in filerefs.LISTINGS
            ):
                self.assertEqual(first, [(ROOT / "re/corpus" / name).read_bytes()
                                         for name in CSV_NAMES])

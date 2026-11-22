"""Regression coverage for packed PE source-path inventories."""

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from tools import srcpaths


ROOT = Path(__file__).resolve().parents[1]
GAME = Path.home() / (
    "Games/lord-of-the-rings-the-return-of-the-king/drive_c/Program Files (x86)/"
    "EA GAMES/LOTR The Return of the King tm"
)


class SourcePathsTest(unittest.TestCase):
    def test_scanner(self):
        ascii_path = b"F:\\EAThirdPerson\\lotr\\rotk\\code\\Kernel\\Example.C"
        wide_path = "c:/DEV/lotr/ROTK/Code/Kernel/example.c"
        for alignment in (0, 1):
            prefix = b"?" + ascii_path + b"\0" + b"\xff" * alignment
            suffix = wide_path.encode("utf-16le") + b"\0\0" + b"\xff"
            blob = prefix + suffix + b"C:\\Dev\\lotr\\rotk\\\0foo.c.exe\0"
            with self.subTest(alignment=alignment):
                self.assertCountEqual(srcpaths.scan(blob), [
                    (1, "ascii", ascii_path.decode()),
                    (len(prefix), "utf-16le", wide_path),
                    (len(prefix + suffix), "ascii", "C:\\Dev\\lotr\\rotk\\"),
                ])
        self.assertEqual(srcpaths.normalize(ascii_path.decode()), "code/kernel/example.c")
        self.assertEqual(srcpaths.normalize(wide_path), "code/kernel/example.c")

    def test_installed_executable_determinism(self):
        exe = Path(os.environ.get("ROTK_GAME_DIR") or GAME) / "ROTK.exe"
        if not exe.is_file():
            self.skipTest("packed ROTK.exe is absent")
        cmd = [sys.executable, "-I", str(ROOT / "tools/srcpaths.py"), str(exe)]
        for flags, report in (
            ([], "re/strings/source_paths.txt"),
            (["--modules"], "docs/modules/README.md"),
        ):
            with self.subTest(report=report):
                first = subprocess.check_output(cmd + flags)
                second = subprocess.check_output(cmd + flags)
                self.assertEqual(first, second)
                self.assertEqual(first, (ROOT / report).read_bytes())
                if not flags:
                    names = []
                    for line in first.decode().splitlines():
                        if line.startswith("#"):
                            continue
                        path, count, records = line.split("\t")
                        names.append(path)
                        hits = json.loads(records)
                        self.assertEqual(len(hits), int(count))
                        self.assertTrue(all(hit[0].startswith("0x") for hit in hits))
                    self.assertEqual(names, sorted(set(names)))

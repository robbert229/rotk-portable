"""CLI regression tests using synthetic symbol records."""

import csv
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "symdb"
HEADER = "address,size,name,unit,module,kind,signature,status,evidence\n"


class SymdbTest(unittest.TestCase):
    def run_cli(self, command, *paths):
        return subprocess.run(
            [sys.executable, "-I", str(ROOT / "tools" / "symdb.py"), command, *paths],
            cwd=ROOT, capture_output=True, text=True,
        )

    def test_fixture_lint(self):
        example = FIXTURES / "Example.csv"
        library = FIXTURES / "lib_example.csv"
        self.assertEqual(self.run_cli("lint", example, library).returncode, 0)
        broken = self.run_cli("lint", FIXTURES / "Broken.csv")
        self.assertEqual(broken.returncode, 1)
        for line, message in (
            (2, "hex VA"), (2, "unit must"), (2, "unknown kind"), (2, "name must"),
            (2, "evidence requires"), (3, "hex byte count"), (3, "unknown status"),
            (3, "FUN_ placeholders"), (3, "evidence requires"),
        ):
            with self.subTest(line=line, message=message):
                self.assertRegex(broken.stderr, rf"Broken.csv:{line}: .*{message}")

    def test_conflicting_files(self):
        for filename, diagnostic in (
            ("Duplicate.csv", "duplicate address"),
            ("Overlap.csv", "overlapping range"),
        ):
            with self.subTest(filename=filename):
                with TemporaryDirectory() as directory:
                    paths = [Path(shutil.copyfile(FIXTURES / name, Path(directory) / name))
                             for name in ("Example.csv", filename)]
                    before = [path.read_bytes() for path in paths]
                    for command in ("lint", "merge"):
                        result = self.run_cli(command, *paths)
                        self.assertEqual(result.returncode, 1)
                        self.assertIn(diagnostic, result.stderr)
                        self.assertIn("Example.csv:3", result.stderr)
                        self.assertIn(f"{filename}:2", result.stderr)
                    self.assertEqual([path.read_bytes() for path in paths], before)

    def test_additional_schema_checks(self):
        valid = ["0x401000", "0x1", "Example_Add", "Example/Math", "Example",
                 "func", "int Example_Add(void)", "typed", "[inferred: synthetic type]"]
        cases = (
            ({0: "0x20"}, "hex VA"),
            ({0: "0xFFFFFFFF", 1: "0x2"}, "exceeds the 32-bit image"),
            ({2: "FUN_00401001", 7: "auto"}, "must identify the function VA"),
            ({2: "FUN_00401000"}, "require eight uppercase hex digits and status=auto"),
            ({4: "Other"}, "match the CSV filename stem"),
            ({5: "lib"}, "requires a lib_* file"),
            ({5: "vtable"}, "vtable names must end"),
            ({6: ""}, "requires a signature"),
            ({7: "nonmatching", 1: "0x00"}, "requires a function with a known size"),
            ({7: "verified", 5: "data"}, "requires a function with a known size"),
            ({8: "[observed: ]"}, "evidence requires"),
            ({8: " [observed: padded]"}, "trimmed single-line text"),
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "Example.csv"
            for changes, diagnostic in cases:
                with self.subTest(changes=changes):
                    row = valid.copy()
                    for index, value in changes.items():
                        row[index] = value
                    with path.open("w", newline="", encoding="utf-8") as stream:
                        stream.write(HEADER)
                        csv.writer(stream).writerow(row)
                    result = self.run_cli("lint", path)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(f"Example.csv:2: ", result.stderr)
                    self.assertIn(diagnostic, result.stderr)
            for contents, diagnostic in (
                ("address\n", "expected header"),
                (HEADER + "0x400000\n", "expected 9 columns"),
                (HEADER + '"unterminated\n', "unexpected end of data"),
            ):
                path.write_text(contents, encoding="utf-8")
                self.assertIn(diagnostic, self.run_cli("lint", path).stderr)
            library = Path(directory) / "lib_example.csv"
            library.write_text(
                HEADER + "0x401000,0x1,example,,lib_example,func,,auto,\n",
                encoding="utf-8",
            )
            self.assertIn("lib_* files require kind=lib", self.run_cli("lint", library).stderr)

    def test_merge_and_exports(self):
        with TemporaryDirectory() as directory:
            paths = [Path(shutil.copyfile(FIXTURES / name, Path(directory) / name))
                     for name in ("Example.csv", "lib_example.csv")]
            exports = {
                "export-ghidra": (
                    "address,size,name,kind,signature\n"
                    '0x00401000,0x10,Example_Add,func,"int __cdecl Example_Add(int a, int b)"\n'
                    "0x00401010,0x1,FUN_00401010,func,\n"
                    "0x00401011,0x0,example,lib,\n"
                ),
                "export-hooks": (
                    "address,name,signature,enabled_by_default\n"
                    '0x00401000,Example_Add,"int __cdecl Example_Add(int a, int b)",false\n'
                ),
            }
            for command, expected in exports.items():
                self.assertEqual(self.run_cli(command, *paths).stdout, expected)
            self.assertEqual(self.run_cli("merge", *paths).returncode, 0)
            canonical = [path.read_bytes() for path in paths]
            self.assertTrue(canonical[0].startswith(HEADER.encode() + b"0x00401000,0x10,"))
            self.assertEqual(self.run_cli("merge", *reversed(paths)).returncode, 0)
            self.assertEqual([path.read_bytes() for path in paths], canonical)
            for command, expected in exports.items():
                self.assertEqual(self.run_cli(command, *reversed(paths)).stdout, expected)

    def test_stats(self):
        result = self.run_cli("stats", FIXTURES / "Example.csv", FIXTURES / "lib_example.csv")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Example (2) auto=50.0% named=0.0% typed=0.0% decomp=50.0%", result.stdout)
        self.assertIn("lib_example (1) auto=0.0% named=100.0%", result.stdout)
        self.assertIn("TOTAL (3) auto=33.3% named=33.3%", result.stdout)

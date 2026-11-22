"""Headless command tests and an opt-in local PE round trip."""

import contextlib
import csv
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from tools import ghidra_build as ghidra

ROOT = ghidra.ROOT
FIXTURE = ROOT / "tests/fixtures/ghidra/fixture.csv"


class HeadlessCommandTests(unittest.TestCase):
    def test_import_quotes_paths_via_argument_boundaries(self):
        args = ghidra.parse_args(["/path with spaces/ROTK.exe"])
        command = self.command(args)
        self.assertEqual(command[:5], [
            "/ghidra/analyzeHeadless", "/projects", "ROTK", "-import",
            "/path with spaces/ROTK.exe",
        ])
        self.assertNotIn("-overwrite", command)
        self.assertNotIn("ExportSymbols.java", command)

    def test_existing_program_and_optional_export(self):
        args = ghidra.parse_args(["ROTK.exe", "--name", "packed", "--export-auto", "auto.csv"])
        command = self.command(args, existing=True)
        self.assertEqual(command[2:5], ["packed", "-process", "ROTK.exe"])
        self.assertEqual(command[-6:], [
            "-postScript", "ExportSymbols.java", "/run/symbols.csv",
            "/run/export/auto.csv", "auto", "/run/summary.txt",
        ])

    def test_reimport_and_symbol_selection(self):
        args = ghidra.parse_args(["ROTK.exe", "--reimport", "--symbols", "a.csv", "b.csv"])
        self.assertEqual(args.symbols, [Path("a.csv"), Path("b.csv")])
        self.assertEqual(self.command(args, existing=True)[3:6],
                         ["-import", "ROTK.exe", "-overwrite"])

    def test_project_name_cannot_escape_output_directory(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            ghidra.parse_args(["ROTK.exe", "--name", "../escape"])
        self.assertEqual(error.exception.code, 2)

    def command(self, args, existing=False):
        return ghidra.headless_command(
            Path("/ghidra/analyzeHeadless"), Path("/projects"),
            args, Path("/run"), existing, "digest",
        )


@unittest.skipUnless(os.environ.get("ROTK_GHIDRA_IT") == "1", "set ROTK_GHIDRA_IT=1")
class HeadlessIntegrationTest(unittest.TestCase):
    def test_fixture_round_trip(self):
        game = Path(os.environ.get("ROTK_GAME_DIR") or ghidra.GAME)
        exe = game / "eauninstall.exe"
        out = ROOT / "out"
        out.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="ghidra-it-", dir=out) as directory:
            work = Path(directory)
            name = work.name
            export = work / "unassigned.csv"
            command = [
                sys.executable, "-BI", str(ROOT / "tools/ghidra_build.py"),
                str(exe), "--name", name, "--export-auto", str(export), "--symbols",
            ]
            try:
                first = self.run_cli([*command, str(FIXTURE)])
                self.assertIn("Ghidra mode: import", first)
                self.assertIn("symbols applied: 1, conflicts: 0", first)
                self.assertEqual(self.run_cli([
                    sys.executable, "-BI", str(ROOT / "tools/symdb.py"), "lint",
                    str(FIXTURE), str(export),
                ]), "")
                with export.open(newline="") as stream:
                    rows = list(csv.DictReader(stream))
                self.assertTrue(rows)
                self.assertTrue(all(row["status"] == "auto" for row in rows))
                self.assertNotIn("0x00409E1F", {row["address"] for row in rows})

                auto = work / "candidate.csv"
                auto.write_text(
                    "address,size,name,unit,module,kind,signature,status,evidence\n"
                    "0x00409E1F,0x0,FUN_00409E1F,,candidate,func,,auto,\n",
                    encoding="utf-8",
                )
                second = self.run_cli([*command, str(auto)])
                self.assertIn("Ghidra mode: process", second)
                self.assertIn("would replace user-defined symbol Fixture_Entry", second)
                self.assertIn("symbols applied: 0, conflicts: 1", second)
            finally:
                projects = out / "ghidra"
                for suffix in (".gpr", ".lock", ".lock~"):
                    (projects / (name + suffix)).unlink(missing_ok=True)
                repository = projects / (name + ".rep")
                if repository.exists():
                    shutil.rmtree(repository)

    def run_cli(self, command):
        result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout)
        return result.stdout

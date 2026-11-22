"""Run the tool CLIs and compare their output with reviewed SHA-256 baselines."""

import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib


REPO = Path(__file__).resolve().parents[1]
EXPECTED = Path(__file__).with_name("expected.json")
SAMPLES = Path(os.environ.get("ROTK_SAMPLES_DIR", REPO / "assets/samples")).resolve()

CASES = {
    "scwdump_text": ("LoadOnce.scw", "scwdump", ("LoadOnce.scw",), "LoadOnce.txt"),
    "scwdump_json": ("LoadOnce.scw", "scwdump", ("LoadOnce.scw", "--json"), "LoadOnce.json"),
    "geo2obj": ("Ring.GEO", "geo2obj", ("Ring.GEO", "-o", "{out}/Ring.obj"), None),
    "txw2png": ("Ring.txw", "txw2png", ("Ring.txw", "-o", "{out}"), None),
    "unpac": (None, "unpac", ("extract", "data_1.pac", "data_2.pac",
                              "--all", "-o", "{out}"), None),
}


def write_synthetic_packs(directory):
    payload = b"synthetic payload"
    toc = struct.pack("<I", 1) + b"Game\\test.bin\0" + bytes(8)
    toc += struct.pack("<I", len(payload))
    for index, block in enumerate((toc + payload[:3], payload[3:]), start=1):
        compressed = zlib.compress(block)
        header = b"x" * 128 + b"\0" + struct.pack("<II", len(block), len(compressed))
        (directory / f"data_{index}.pac").write_bytes(header + compressed)


def output_hashes(case):
    sample, tool, arguments, stdout_file = CASES[case]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        output = root / "output"
        output.mkdir()
        if sample is None:
            write_synthetic_packs(root)
        result = subprocess.run(
            [sys.executable, "-I", str(REPO / "tools" / f"{tool}.py"),
             *(argument.format(out=output) for argument in arguments)],
            cwd=SAMPLES if sample else root,
            capture_output=True,
            timeout=30,
        )
        if result.returncode:
            raise RuntimeError(f"{tool} exited with {result.returncode}\n"
                               f"{result.stderr.decode(errors='replace')}")
        if stdout_file:
            (output / stdout_file).write_bytes(result.stdout)
        return {
            path.relative_to(output).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(output.rglob("*")) if path.is_file()
        }


class ToolRegressionTest(unittest.TestCase):
    def assert_output_matches(self, case):
        sample = CASES[case][0]
        if sample and not (SAMPLES / sample).is_file():
            self.skipTest(f"missing sample {SAMPLES / sample}; set ROTK_SAMPLES_DIR")
        expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
        self.assertEqual(output_hashes(case), expected[case])

    def test_scwdump_text(self):
        self.assert_output_matches("scwdump_text")

    def test_scwdump_json(self):
        self.assert_output_matches("scwdump_json")

    def test_geo2obj(self):
        self.assert_output_matches("geo2obj")

    def test_txw2png(self):
        self.assert_output_matches("txw2png")

    def test_unpac_split_pac(self):
        self.assert_output_matches("unpac")


def update_expected():
    missing = {SAMPLES / sample for sample, *_ in CASES.values()
               if sample and not (SAMPLES / sample).is_file()}
    if missing:
        sys.exit("Missing samples: " + ", ".join(map(str, sorted(missing))))
    expected = {case: output_hashes(case) for case in CASES}
    if not all(expected.values()):
        sys.exit("Cannot update the baseline: a tool produced no files")
    EXPECTED.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1:] == ["--update"]:
        update_expected()
    else:
        unittest.main()

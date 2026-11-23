"""Run the tool CLIs and compare their output with reviewed SHA-256 baselines."""

from collections import Counter
import csv
import hashlib
import io
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
sys.path.insert(0, str(REPO / "tools"))
from corpus import game_dir
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



class ScwWalkTest(unittest.TestCase):
    def dump(self, data):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.scw"
            path.write_bytes(data)
            result = subprocess.run(
                [sys.executable, "-I", str(REPO / "tools/scwdump.py"), str(path), "--json"],
                check=True, capture_output=True, timeout=30,
            )
        return json.loads(result.stdout)

    def test_lrtc_sizes_and_padding(self):
        header = struct.pack("<4sI8x4sI", b"LRTC", 24, b"CNYS", 0)
        descriptor = struct.pack("<4sI8x4sI4sI", b"COHS", 32, b"RDHS", 1, b"TEST", 7)
        data_chunk = struct.pack("<4sI8x4s", b"ONOS", 20, b"TADS")
        # The short LLIF ends at a page boundary and has no size word.
        data = (header + descriptor + data_chunk * 3272
                + struct.pack("<4sI8x4s16x", b"ONOS", 36, b"TADS") + b"LLIF"
                + data_chunk + struct.pack("<4sI", b"LLIF", 0x10000 - 20)
                + bytes(0x10000 - 28))
        scene = self.dump(data)
        self.assertNotIn("stopped_at", scene)
        self.assertEqual(scene["covered"], "0x20000 / 0x20000")
        chunks = scene["chunks"]
        self.assertEqual(len(chunks), 3277)
        self.assertEqual(chunks[0]["index"], [
            {"tag": "RDHS", "v1": "0x1", "off": "0x28"},
            {"tag": "TEST", "v1": "0x7", "off": "0x30"},
        ])
        self.assertEqual(chunks[-3]["size"], 4)
        self.assertEqual(chunks[-2]["offset"], "0x10000")

    def test_lrtc_reports_first_unparsed_offset(self):
        header = struct.pack("<4sI16x", b"LRTC", 24)
        good = struct.pack("<4sI8x4s", b"COHS", 20, b"TADS")
        for tail in (b"COHS", struct.pack("<4sI", b"COHS", 0),
                     struct.pack("<4sI", b"COHS", 20), bytes(4)):
            with self.subTest(tail=tail):
                scene = self.dump(header + good + tail)
                self.assertEqual(len(scene["chunks"]), 1)
                self.assertEqual(scene["stopped_at"]["offset"], "0x2c")

    def test_retail_chunk_inventory(self):
        game = game_dir()
        if not game.is_dir():
            self.skipTest("retail game directory unavailable")
        command = [sys.executable, "-BI", str(REPO / "tools/scwdump.py"), str(game)]
        summary = REPO / "re/corpus/scw_chunk_summary.csv"
        result = subprocess.run(command + ["--summary-csv"], check=True,
                                capture_output=True, timeout=30)
        self.assertEqual(result.stdout, summary.read_bytes())
        with summary.open(newline="") as source:
            summaries = {row["path"]: row for row in csv.DictReader(source)}

        result = subprocess.run(command + ["--chunks-csv"], check=True,
                                capture_output=True, timeout=30)
        counts = Counter()
        depths = {}
        cursors = dict.fromkeys(summaries, 0)
        for row in csv.DictReader(io.StringIO(result.stdout.decode("utf-8"))):
            path = row["path"]
            self.assertEqual(int(row["offset"], 16), cursors[path], path)
            cursors[path] += int(row["size"])
            counts[path, row["tag"]] += 1
            depths[path, row["offset"]] = depths[path, row["parent"]] + 1 if row["parent"] else 0

        tags = ("COTS", "LRTC", "RVWS", "COHS", "ONOS", "DDAP", "LLIF")
        for path, row in summaries.items():
            with self.subTest(path=path):
                for tag in tags:
                    self.assertEqual(counts[path, tag], int(row[tag]), tag)
                leftover = (game / path).stat().st_size - cursors[path]
                self.assertEqual(leftover, int(row["leftover_bytes"]))
                self.assertEqual(row["walked_to_eof"], "yes" if not leftover else "no")
                self.assertEqual(int(row["max_depth"]),
                                 max(depth for (name, _), depth in depths.items() if name == path))


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

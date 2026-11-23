"""Cross-check the checked-in corpus without requiring a game install."""

import csv
from pathlib import Path
import unittest


CORPUS = Path(__file__).resolve().parents[1] / "re/corpus"


def read(name):
    with (CORPUS / f"{name}.csv").open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


class CorpusConsistencyTest(unittest.TestCase):
    def test_install_coverage(self):
        install = {row["path"] for row in read("manifest") if row["origin"] == "install"}
        formats = {row["path"]: row["detected_format"] for row in read("formats")}
        pe = {path for path, detected in formats.items() if detected == "PE"}
        self.assertEqual(install, formats.keys())
        self.assertEqual(pe, {row["path"] for row in read("binaries")})
        self.assertEqual(install - pe, {row["path"] for row in read("assets")})
        self.assertEqual({row["path"]: row["container"] for row in read("assets_scw")},
                         {row["path"]: row["container"] for row in read("scw_chunk_summary")})

    def test_derived_identity(self):
        manifest = {(row["origin"].split(":", 1)[0], row["path"]): row
                    for row in read("manifest")}
        for table in ("formats", "binaries", "assets", "assets_avi", "assets_scw", "samples"):
            seen = set()
            for row in read(table):
                if table == "samples":
                    key = row["source_origin"], row["source_path"]
                else:
                    key = "install", row["path"]
                with self.subTest(table=table, key=key):
                    self.assertNotIn(key, seen)
                    seen.add(key)
                    self.assertIn(key, manifest)
                    self.assertEqual(row["sha256"], manifest[key]["sha256"])
                    self.assertEqual(row["size"], manifest[key]["size"])

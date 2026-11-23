import csv
import hashlib
import io
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import corpus_formats


class FormatDetectionTest(unittest.TestCase):
    def test_content_detection(self):
        bmp = b"BM" + struct.pack("<4I", 58, 0, 54, 40) + bytes(40)
        cases = (
            (b"COTS", "SCW COTS"),
            (b"LRTC", "SCW LRTC"),
            (b"MOEG", "GEO"),
            (b"TXW ", "TXW"),
            (b"RIFF\x04\0\0\0AVI ", "RIFF/AVI"),
            (b"RIFF\x04\0\0\0WAVE", "unknown"),
            (b"\x3f\x5f\x03\x00", "HLP"),
            (b"\0\0\x01\0\x01\0", "ICO"),
            (bmp, "BMP"),
            (b"\xef\xbb\xbf<?xml version='1.0'?><root/>", "XML"),
            ("<root/>".encode("utf-16"), "XML"),
            (b"; comment\r\n[section]\r\na=1\r\na=2\r\n", "INI"),
            (b"[bracketed text]\nno assignment", "plain text"),
            (b"Windows text \x96 with DOS EOF\r\n\x1a", "plain text"),
            (b"foo\0bar", "unknown"),
            (b"", "unknown"),
        )
        for data, expected in cases:
            with self.subTest(expected=expected, prefix=data[:8]):
                source = io.BytesIO(data)
                head = source.read(corpus_formats.PROBE_SIZE)
                self.assertEqual(corpus_formats.detect_format(source, head), expected)

    def test_pe_offset_can_point_past_probe(self):
        pe_offset = corpus_formats.PROBE_SIZE + 16
        dos = b"MZ" + bytes(58) + struct.pack("<I", pe_offset) + bytes(pe_offset - 64)
        for signature, expected in ((b"PE\0\0", "PE"), (b"NE\0\0", "MZ"), (b"", "MZ")):
            with self.subTest(signature=signature):
                source = io.BytesIO(dos + signature)
                head = source.read(corpus_formats.PROBE_SIZE)
                self.assertEqual(corpus_formats.detect_format(source, head), expected)

    def test_audit_uses_content_and_reads_embedded_parser_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            filename = "scene.txt"
            payload = b"COTS" + bytes(20)  # scwdump --json reports error with exit status 0
            (root / filename).write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()
            manifest = root / "manifest.csv"
            manifest.write_text(
                "origin,path,size,sha256\n"
                f"install,{filename},{len(payload)},{digest}\n"
                f"pac:data_1,{filename},{len(payload)},{digest}\n",
                encoding="utf-8",
            )
            self.assertEqual(list(corpus_formats.audit(root, manifest)), [
                (filename, digest, len(payload), ".txt", "SCW COTS", payload[:8].hex(),
                 "docs/formats/scw.md", "tools/scwdump.py", "fail",
                 "missing inner COTS at +0x10"),
            ])


class LocalFormatCorpusTest(unittest.TestCase):
    def test_install_regenerates_committed_csv(self):
        game = Path(os.environ.get("ROTK_GAME_DIR") or corpus_formats.DEFAULT_GAME_DIR)
        if not game.is_dir():
            self.skipTest("retail game directory is absent")
        result = subprocess.run(
            [sys.executable, "-I", str(ROOT / "tools/corpus_formats.py"), "--stdout",
             "--game-dir", str(game)],
            capture_output=True, timeout=300,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
        self.assertEqual(result.stdout, corpus_formats.OUTPUT.read_bytes())
        with corpus_formats.MANIFEST.open(encoding="utf-8", newline="") as manifest:
            expected_paths = sorted(row["path"] for row in csv.DictReader(manifest)
                                    if row["origin"] == "install")
        rendered = io.StringIO(result.stdout.decode("utf-8"), newline="")
        actual_paths = [row["path"] for row in csv.DictReader(rendered)]
        self.assertEqual(actual_paths, expected_paths)
        self.assertEqual(len(actual_paths), len(set(actual_paths)))

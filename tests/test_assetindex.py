"""Synthetic CLI coverage and optional retail asset index regeneration."""

import csv
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote

REPO = Path(__file__).resolve().parents[1]
GAME_DIR = Path(os.environ.get("ROTK_GAME_DIR") or Path.home() / (
    "Games/lord-of-the-rings-the-return-of-the-king/drive_c/"
    "Program Files (x86)/EA GAMES/LOTR The Return of the King tm"
))
CSV_NAMES = ("assets.csv", "assets_scw.csv", "assets_avi.csv")


def chunk(tag, payload):
    return struct.pack("<4sI", tag, len(payload)) + payload


def riff_chunk(tag, payload):
    return chunk(tag, payload) + b"\0" * (len(payload) % 2)


def avi(indexed=False):
    main = struct.pack("<14I", 0, 0, 0, 0, 60, 0, 2, 0, 640, 480, 0, 0, 0, 0)
    video = struct.pack("<4s4s10I4h", b"vids", b"DXGM", 0, 0, 0, 1001, 30000,
                        0, 60, 0, 0, 0, 0, 0, 0, 0)
    bitmap = struct.pack("<IiiHH4s20x", 40, 640, -480, 1, 24, b"DXGM")
    audio = b"auds" + bytes(52)
    headers = (riff_chunk(b"avih", main)
               + riff_chunk(b"LIST", b"strl" + riff_chunk(b"strh", video)
                            + riff_chunk(b"strf", bitmap))
               + riff_chunk(b"LIST", b"strl" + riff_chunk(b"strh", audio)))
    # Fake index tags in opaque data cannot satisfy the index check.
    payload = (b"AVI " + riff_chunk(b"JUNK", b"idx1!")
               + riff_chunk(b"LIST", b"hdrl" + headers)
               + riff_chunk(b"LIST", b"movi" + riff_chunk(b"00dc", b"idx1")))
    if indexed:
        payload += riff_chunk(b"idx1", bytes(16))
    return riff_chunk(b"RIFF", payload) + riff_chunk(b"JUNK", b"idx1")


def cots():
    names = (b"initial_load", b"zone_sample", b"_missingZone_03", b"igc_samplebank",
             b"igc_sample_zone")
    pool = b""
    records = b""
    pool_start = 0x28 + 16 * len(names) + 4
    docs = b""
    for index, name in enumerate(names):
        doc = b""
        if not name.startswith(b"_missing"):
            doc = chunk(b"RVWS", b"ELIF" + (name + b"\0").ljust(24, b"\0")) + b"LRTC"
        records += struct.pack("<4I", len(names) if index == 0 else index,
                               pool_start + len(pool), 0x200 + len(docs), len(doc))
        pool += name + b"\0"
        docs += doc
    llif = pool_start + len(pool)
    header = struct.pack("<4s3I4s5I", b"COTS", llif, 0, 0, b"COTS",
                         llif - 0x18 + 4, len(names), 1, 0, 0)
    return (header + records + bytes(4) + pool + chunk(b"LLIF", b"")).ljust(0x200, b"\0") + docs


def txw():
    entry = bytearray(80)
    entry[:4] = b"test"
    struct.pack_into("<HHB", entry, 0x38, 32, 16, 1)
    entry[0x41] = 7
    return b"TXW " + struct.pack("<I", 528) + chunk(b"TXHE", entry)


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as source:
        return {row["path"]: row for row in csv.DictReader(source)}


def details(row):
    return {part.split("=", 1)[0]: unquote(part.split("=", 1)[1])
            for part in row["details"].split(";") if part}


def regenerate(game, manifest, dest):
    return subprocess.run(
        [sys.executable, "-BI", str(REPO / "tools/assetindex.py"), "--game-dir", str(game),
         "--manifest", str(manifest), "--out-dir", str(dest)],
        capture_output=True, text=True, cwd=dest.parent,
    )


class AssetIndexTest(unittest.TestCase):
    def test_synthetic_index(self):
        pe = bytearray(68)
        pe[:2] = b"MZ"
        struct.pack_into("<I", pe, 0x3C, 64)
        pe[64:] = b"PE\0\0"
        files = {
            "one.avi": avi(),
            "indexed.avi": avi(indexed=True),
            "mission.scw": cots(),
            "global.scw": b"LRTC" + struct.pack("<5I", 24, 0, 0, 0, 0)
            + chunk(b"COHS", b"RDHS" + struct.pack("<I", 1)) + bytes(8) + b"TADSxxxx",
            "element.xml": b"<root><z>secret</z><a><b/></a><z/></root>",
            "input.ini": b"\xef\xbb\xbf[section]\r\n;secret\r\nkey=secret\n",
            "manual.txt": b"caf\xe9\rline",
            "test.GEO": b"MOEG" + struct.pack("<3I8fI3H", 1, 1, 1, *([0] * 8), 3, 0, 0, 0),
            "test.txw": txw(),
            "bitmap.256": b"BM",
            "empty.bin": b"",
            "code.dat": bytes(pe),
            "data.exe": b"not a PE file",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            game = root / "game with spaces" / "drive_c" / "install"
            game.mkdir(parents=True)
            manifest = root / "manifest.csv"
            output = root / "output"
            with manifest.open("w", encoding="utf-8", newline="") as source:
                writer = csv.writer(source)
                writer.writerow(("origin", "path", "size", "sha256"))
                for name, data in files.items():
                    (game / name).write_bytes(data)
                    writer.writerow(("install", name, len(data), hashlib.sha256(data).hexdigest()))
                writer.writerow(("pac:data_1", "noninstall.avi", 0, "ignored"))
            result = regenerate(game, manifest, output)
            self.assertEqual(result.returncode, 0, result.stderr)
            assets = read_rows(output / "assets.csv")
            self.assertEqual(list(assets), sorted(files.keys() - {"code.dat"}))
            self.assertEqual(assets["bitmap.256"]["format"], "BMP")
            self.assertEqual(assets["empty.bin"]["size"], "0")
            self.assertIn("reason", details(assets["empty.bin"]))
            self.assertEqual(details(assets["element.xml"]), {"root": "root", "child_tags": "a|z"})
            self.assertEqual(assets["element.xml"]["element_count"], "5")
            self.assertEqual(assets["input.ini"]["line_count"], "3")
            self.assertEqual(assets["input.ini"]["section_count"], "1")
            self.assertEqual(assets["input.ini"]["encoding"], "utf-8-sig")
            self.assertEqual(assets["manual.txt"]["encoding"], "cp1252-compatible")
            self.assertEqual(assets["manual.txt"]["line_count"], "2")
            self.assertEqual(assets["test.GEO"]["mesh_count"], "1")
            self.assertEqual(details(assets["test.GEO"])["triangle_count"], "1")
            self.assertEqual(assets["test.txw"]["texture_count"], "1")
            self.assertEqual(details(assets["test.txw"])["textures"], "test:32x16:1")

            scenes = read_rows(output / "assets_scw.csv")
            mission = scenes["mission.scw"]
            for key, expected in {"toc_count": "5", "zone_count": "1", "missing_zone_count": "1",
                                  "bank_count": "1", "other_igc_count": "1",
                                  "chunk_count": "2", "chain_contiguous": "1"}.items():
                self.assertEqual(mission[key], expected, key)
            self.assertEqual(mission["embedded_doc_names"],
                             "initial_load|zone_sample||igc_samplebank|igc_sample_zone")
            self.assertEqual(scenes["global.scw"]["chunk_count"], "1")
            self.assertEqual(scenes["global.scw"]["walk_end"], "0x30")

            videos = read_rows(output / "assets_avi.csv")
            self.assertEqual(videos["indexed.avi"]["has_index"], "1")
            self.assertEqual(videos["indexed.avi"]["index_types"], "idx1")
            video = videos["one.avi"]
            for key, expected in {"width": "640", "height": "480", "frame_count": "60",
                                  "duration_seconds": "2.002000", "fps": "29.970030",
                                  "codec": "DXGM", "stream_count": "2", "has_audio": "1",
                                  "has_index": "0", "bytes_after_riff": "12"}.items():
                self.assertEqual(video[key], expected, key)

            for name in CSV_NAMES:
                self.assertNotIn(b"secret", (output / name).read_bytes())

            result = regenerate(game, manifest, game.parents[1] / "forbidden")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("inside the game prefix", result.stderr)
            (game / "data.exe").write_bytes(b"?" * len(files["data.exe"]))
            original = {name: (output / name).read_bytes() for name in CSV_NAMES}
            result = regenerate(game, manifest, output)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SHA-256 differs from manifest", result.stderr)
            self.assertEqual(original, {name: (output / name).read_bytes() for name in CSV_NAMES})

    @unittest.skipUnless(GAME_DIR.is_dir(), "retail game directory unavailable")
    def test_retail_regeneration(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            corpus = REPO / "re/corpus"
            result = regenerate(GAME_DIR, corpus / "manifest.csv", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in CSV_NAMES:
                self.assertEqual((output / name).read_bytes(), (corpus / name).read_bytes(), name)

import csv
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib


class CorpusTest(unittest.TestCase):
    def test_manifest_with_split_pac_member(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tools = root / "tools"
            tools.mkdir()
            for name in ("corpus.py", "unpac.py"):
                shutil.copyfile(Path(__file__).resolve().parents[1] / "tools" / name,
                                tools / name)
            game = root / "game install"
            (game / "Data" / "Game").mkdir(parents=True)
            payload = b"synthetic payload"
            (game / "Data" / "Game" / "test.bin").write_bytes(payload)
            toc = struct.pack("<I", 1) + b"Game\\test.bin\0" + bytes(8)
            toc += struct.pack("<I", len(payload))
            packs = [root / f"data_{index}.pac" for index in (1, 2)]
            for pack, logical in zip(packs, (toc + payload[:3], payload[3:])):
                compressed = zlib.compress(logical)
                pack.write_bytes(b"x" * 128 + b"\0"
                                 + struct.pack("<II", len(logical), len(compressed))
                                 + compressed)
            subprocess.run(
                [sys.executable, "-I", str(tools / "corpus.py"), "--pac", *packs],
                env={**os.environ, "ROTK_GAME_DIR": str(game)},
                check=True, capture_output=True, text=True,
            )
            with (root / "re/corpus/manifest.csv").open(newline="") as manifest:
                digest = hashlib.sha256(payload).hexdigest()
                self.assertEqual(list(csv.reader(manifest)), [
                    ["origin", "path", "size", "sha256"],
                    ["install", "Data/Game/test.bin", str(len(payload)), digest],
                    ["pac:data_1", "Game/test.bin", str(len(payload)), digest],
                ])

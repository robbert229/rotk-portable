import csv
import hashlib
import io
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib


def write_pack(path, logical):
    compressed = zlib.compress(logical)
    path.write_bytes(b"x" * 128 + b"\0"
                     + struct.pack("<II", len(logical), len(compressed))
                     + compressed)


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
                write_pack(pack, logical)
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

    def run_corpus(self, *args, game, media):
        tools = game.parent / "tools"
        tools.mkdir(exist_ok=True)
        for name in ("corpus.py", "unpac.py"):
            shutil.copyfile(Path(__file__).resolve().parents[1] / "tools" / name,
                            tools / name)
        return subprocess.run(
            [sys.executable, "-I", str(tools / "corpus.py"), *args],
            env={**os.environ, "ROTK_GAME_DIR": str(game), "ROTK_ISO_DIR": str(media)},
            capture_output=True, text=True,
        )

    def test_verify_reports_four_statuses(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            game = root / "install"
            data = game / "Data/Game"
            data.mkdir(parents=True)
            (game / "readme.txt").write_bytes(b"outside Data")
            (data / "Match.scw").write_bytes(b"same")
            (data / "diff.scw").write_bytes(b"bad")
            (data / "loose.scw").write_bytes(b"loose")
            members = [(b"Game", b""), (b"Game\\match.scw", b"same"),
                       (b"Game\\diff.scw", b"pac"), (b"Game\\extra.scw", b"extra")]
            toc = struct.pack("<I", len(members))
            for name, payload in members:
                toc += name + bytes(9) + struct.pack("<I", len(payload))
            stream = toc + b"".join(payload for _, payload in members)
            media = root / "media"
            for number, logical in enumerate((stream[:-6], stream[-6:-3], stream[-3:]), 1):
                disc = media / f"disc{number}"
                disc.mkdir(parents=True)
                write_pack(disc / f"data_{number}.pac", logical)

            result = self.run_corpus("--verify", game=game, media=media)
            self.assertEqual(result.returncode, 1, result.stderr)
            report, summary, _ = result.stdout.rsplit("\n", 2)
            self.assertEqual(summary, "Summary match=1, mismatch=1, pac-only=1, install-only=1")
            rows = list(csv.DictReader(io.StringIO(report)))
            self.assertEqual([(row["status"], row["path"]) for row in rows], [
                ("mismatch", "Data/Game/diff.scw"),
                ("pac-only", "Data/Game/extra.scw"),
                ("install-only", "Data/Game/loose.scw"),
                ("match", "Data/Game/match.scw"),
            ])
            self.assertEqual(rows[0]["pac_sha256"], hashlib.sha256(b"pac").hexdigest())
            self.assertEqual(rows[0]["install_sha256"], hashlib.sha256(b"bad").hexdigest())
            self.assertEqual(rows[1]["install_sha256"], "")
            self.assertEqual(rows[2]["pac_size"], "")

            (data / "diff.scw").write_bytes(b"pac")
            result = self.run_corpus("--verify", "--disc-tree", media / "disc1",
                                     "--disc-label", "TEST CD", game=game, media=media)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Summary match=2, mismatch=0, pac-only=1, install-only=1", result.stderr)
            row, = csv.DictReader(io.StringIO(result.stdout))
            self.assertEqual(row["volume_label"], "TEST CD")
            self.assertFalse((root / "re/corpus/manifest.csv").exists())

    def test_disc_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trees = [root / "disc1", root / "disc2"]
            (trees[0] / "Support").mkdir(parents=True)
            trees[1].mkdir()
            (trees[0] / "Support/setup.txt").write_bytes(b"help")
            (trees[1] / "data_2.pac").write_bytes(b"disc two")
            images = [root / "one.iso", root / "two.bin"]
            boot = b"\x00CD001\x01".ljust(2048, b"\0")
            descriptors = []
            for label in (b"TEST CD 1", b"TEST CD 2"):
                pvd = bytearray(b"\x01CD001\x01".ljust(2048, b"\0"))
                pvd[40:72] = label.ljust(32)
                descriptors.append(pvd)
            images[0].write_bytes(bytes(16 * 2048) + boot + descriptors[0])
            images[1].write_bytes(bytes(16 * 2352 + 16) + descriptors[1] + bytes(288))

            result = self.run_corpus("--disc-tree", *trees, "--disc-image", *images,
                                     game=root / "absent install", media=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = list(csv.reader(io.StringIO(result.stdout)))

            def expected(origin, kind, path, data, label):
                return [origin, kind, path, str(len(data)), hashlib.sha256(data).hexdigest(), label]

            self.assertEqual(rows, [
                ["origin", "kind", "path", "size", "sha256", "volume_label"],
                expected("disc1", "image", "one.iso", images[0].read_bytes(), "TEST CD 1"),
                expected("disc1", "file", "Support/setup.txt", b"help", "TEST CD 1"),
                expected("disc2", "image", "two.bin", images[1].read_bytes(), "TEST CD 2"),
                expected("disc2", "file", "data_2.pac", b"disc two", "TEST CD 2"),
            ])

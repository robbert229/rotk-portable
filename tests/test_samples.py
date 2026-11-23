"""Exercise the sample CLI with synthetic sources in isolated temp trees."""

import csv
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


TOOL = Path(__file__).resolve().parents[1] / "tools/samples.py"
FIELDS = (
    "sample_id", "source_origin", "source_path", "sha256", "size",
    "format", "variant", "why_selected", "used_by_tests",
)
PAYLOAD = b"sample!"


class SamplesTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.install = self.root / "Game install"
        self.install.mkdir()
        self.manifest = self.root / "samples.csv"
        self.output = self.root / "assets/samples"
        self.source = self.install / "Data/Video.avi"
        self.source.parent.mkdir()
        self.source.write_bytes(PAYLOAD)
        self.canonical = self.output / "riff-avi/Data/Video.avi"
        self.flat = self.output / "Video.avi"
        self.install_row = self.row("video", "install", "Data/Video.avi", fmt="RIFF/AVI",
                                    used_by_tests="yes")
        self.write_manifest(self.install_row)

    @staticmethod
    def row(sample_id, origin, path, fmt="BMP", used_by_tests="no"):
        return (sample_id, origin, path, hashlib.sha256(PAYLOAD).hexdigest(),
                len(PAYLOAD), fmt, "synthetic", "test fixture", used_by_tests)

    def write_manifest(self, *rows):
        with self.manifest.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(FIELDS)
            writer.writerows(rows)

    def cli(self, command, *args, code=0, output=None):
        result = subprocess.run(
            [sys.executable, "-I", str(TOOL), command, "--manifest", str(self.manifest),
             "--game-dir", str(self.install), "--samples-dir", str(output or self.output),
             *args],
            cwd=self.root, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def test_fetch_check_and_idempotence(self):
        self.cli("fetch")
        self.assertEqual(self.canonical.read_bytes(), PAYLOAD)
        self.assertEqual(self.flat.read_bytes(), PAYLOAD)
        self.cli("check")
        canonical_stat = self.canonical.stat()
        flat_stat = self.flat.stat()
        self.source.unlink()
        self.cli("fetch")
        self.assertEqual(self.canonical.stat().st_mtime_ns, canonical_stat.st_mtime_ns)
        self.assertEqual(self.flat.stat().st_mtime_ns, flat_stat.st_mtime_ns)
        self.flat.unlink()
        self.cli("fetch")
        self.assertEqual(self.flat.read_bytes(), PAYLOAD)

    def test_corrupt_source_does_not_replace_destination(self):
        self.cli("fetch")
        self.canonical.write_bytes(b"damaged")
        self.assertIn("SHA-256 mismatch", self.cli("check", code=1).stderr)
        self.source.write_bytes(b"invalid")
        self.assertIn("SHA-256 mismatch", self.cli("fetch", code=1).stderr)
        self.assertEqual(self.canonical.read_bytes(), b"damaged")
        self.assertEqual(list(self.canonical.parent.iterdir()), [self.canonical])
        self.assertEqual(self.source.read_bytes(), b"invalid")
        self.source.write_bytes(PAYLOAD)
        self.cli("fetch")
        self.cli("check")

    def test_size_mismatch_does_not_publish_file(self):
        self.source.write_bytes(PAYLOAD + b"extra")
        self.assertIn("size mismatch", self.cli("fetch", code=1).stderr)
        self.assertEqual(list(self.canonical.parent.iterdir()), [])

    def test_missing_sources_are_reported_and_other_rows_copy(self):
        self.write_manifest(self.row("pac-file", "pac", "Game/member.bmp"),
                            self.row("missing", "install", "missing.bmp"), self.install_row)
        errors = self.cli("fetch", code=1).stderr
        self.assertIn("missing pac source Game/member.bmp", errors)
        self.assertIn("missing install source", errors)
        self.assertEqual(self.canonical.read_bytes(), PAYLOAD)
        pac_dir = self.root / "Extracted PACs"
        member = pac_dir / "Game/member.bmp"
        member.parent.mkdir(parents=True)
        member.write_bytes(PAYLOAD)
        (self.install / "missing.bmp").write_bytes(PAYLOAD)
        self.cli("fetch", "--pac-dir", str(pac_dir))
        self.assertEqual((self.output / "bmp/Game/member.bmp").read_bytes(), PAYLOAD)
        self.cli("check")

    def test_fetch_rejects_output_inside_install(self):
        output = self.install / "samples"
        self.assertIn("inside a source directory", self.cli("fetch", code=1, output=output).stderr)
        self.assertFalse(output.exists())

    def test_fetch_rejects_symlinked_destination_parent(self):
        self.output.mkdir(parents=True)
        (self.output / "riff-avi").symlink_to(self.install, target_is_directory=True)
        self.assertIn("unsafe sample destination", self.cli("fetch", code=1).stderr)
        self.assertEqual(self.source.read_bytes(), PAYLOAD)
        self.assertFalse(self.flat.exists())

    def test_fetch_rejects_parent_traversal_before_copying(self):
        self.write_manifest(self.install_row, self.row("escape", "install", "../outside"))
        self.assertIn("invalid relative source path", self.cli("fetch", code=1).stderr)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()

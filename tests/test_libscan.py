"""Offline library fingerprints and reference cache tests."""
import csv
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest

from tools import libscan, refs, richhdr


def fixture_pe(payload):
    """Minimal PE32 with an EAX import and a valid Rich C compiler record."""
    data = bytearray(0x600)
    data[:2] = b"MZ"
    pe = 0xb0
    struct.pack_into("<I", data, 0x3c, pe)
    compid = (28 << 16) | 9466
    key = 0x80 + ord("M") + richhdr.rol(ord("Z"), 1) + richhdr.rol(compid, 2)
    struct.pack_into("<6I4sI", data, 0x80, richhdr.DANS ^ key, key, key, key,
                     compid ^ key, 2 ^ key, b"Rich", key)
    struct.pack_into("<4sHHIIIHH", data, pe, b"PE\0\0", 0x14c, 1, 0, 0, 0, 0xe0, 2)
    optional = pe + 24
    struct.pack_into("<H", data, optional, 0x10b)
    struct.pack_into("<I", data, optional + 28, 0x400000)
    struct.pack_into("<II", data, optional + 32, 0x1000, 0x200)
    struct.pack_into("<II", data, optional + 56, 0x2000, 0x200)
    struct.pack_into("<I", data, optional + 92, 16)
    struct.pack_into("<II", data, optional + 104, 0x1000, 40)
    struct.pack_into("<8s4I", data, optional + 0xe0, b".rdata", 0x400, 0x1000, 0x400, 0x200)
    struct.pack_into("<5I", data, 0x200, 0x1070, 0, 0, 0x1040, 0x1070)
    data[0x240:0x248] = b"eax.dll\0"
    data[0x280:0x280 + len(payload)] = payload
    return data


class LibraryScanTest(unittest.TestCase):
    def test_pe_offsets_and_versions(self):
        payload = b"inflate 1.1.4 Copyright 1995-2002 Mark Adler\0"
        hits = set(libscan.scan(fixture_pe(payload)))
        self.assertIn(libscan.Hit("zlib", "1.1.4", "string", 0x280, payload[:-1].decode()), hits)
        self.assertIn(libscan.Hit("EAX Unified", "unknown", "import", 0x240, "eax.dll"), hits)
        self.assertIn(libscan.Hit("Microsoft build tools", "Visual Studio .NET 2002 RTM",
                                  "rich", 0x90, "Utc13_C 28/9466 x2 (valid)"), hits)
        self.assertTrue(all(len(hit.row("fixture.exe")[5]) <= 80 for hit in hits))

    def test_version_literal_requires_context(self):
        data = fixture_pe(b"\0" + b"1.1.3\0incorrect header check\0invalid distance code\0")
        hits = set(libscan.scan(data))
        self.assertIn(libscan.Hit("zlib", "1.1.3", "string", 0x281,
                                  "1.1.3 near inflate errors", "inferred"), hits)
        self.assertFalse(any(hit.library == "zlib" for hit in libscan.scan(fixture_pe(b"1.1.3\0"))))

    def test_crc_requires_full_table(self):
        values = []
        for value in range(256):
            for _ in range(8):
                value = (value >> 1) ^ (0xedb88320 if value & 1 else 0)
            values.append(value)
        table = struct.pack("<256I", *values)
        blob = b"junk" + table
        hit = libscan.Hit("CRC-32", "unknown", "table", 4, "IEEE CRC-32 look-up table")
        self.assertEqual(list(libscan.table_hits(blob)), [hit])
        self.assertEqual(list(libscan.table_hits(blob[:-1])), [])
        self.assertEqual(list(libscan.table_hits(blob[:-1] + bytes([blob[-1] ^ 1]))), [])

    def test_invalid_pe_fails(self):
        with self.assertRaises(ValueError):
            list(libscan.scan(b"not an executable"))


class ReferencesTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.source = root / "fixture.tar.gz"
        self.source.write_bytes(b"test archive")
        self.cache = root / "refs"
        self.target = self.cache / self.source.name
        self.manifest = root / "refs.csv"
        digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        with self.manifest.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(("kind", "path", "download_url", "sha256"))
            pin = ("archive", self.source.name, self.source.as_uri(), digest)
            writer.writerows([pin, pin])

    def test_fetch_and_offline_cache_hit(self):
        refs.fetch(self.manifest, self.cache)
        self.assertEqual(self.target.read_bytes(), b"test archive")
        self.source.unlink()
        refs.fetch(self.manifest, self.cache)
        self.assertEqual(list(self.cache.iterdir()), [self.target])

    def test_refuses_bad_download_without_publishing(self):
        self.source.write_bytes(b"wrong archive")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            refs.fetch(self.manifest, self.cache)
        self.assertEqual(list(self.cache.iterdir()), [])

    def test_refuses_existing_mismatch(self):
        self.cache.mkdir()
        self.target.write_bytes(b"wrong cached archive")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            refs.fetch(self.manifest, self.cache)
        self.assertEqual(self.target.read_bytes(), b"wrong cached archive")

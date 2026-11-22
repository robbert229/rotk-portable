#!/usr/bin/env python3
"""Hash the ROTK installation and optional retail PAC members."""

import argparse
from bisect import bisect_right
import csv
import hashlib
import os
from pathlib import Path
import sys
import tempfile

# Isolated script execution does not add the script directory to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from unpac import Archive, PacError

DEFAULT_GAME_DIR = Path.home() / (
    "Games/lord-of-the-rings-the-return-of-the-king/drive_c/"
    "Program Files (x86)/EA GAMES/LOTR The Return of the King tm"
)
MANIFEST = Path(__file__).resolve().parents[1] / "re/corpus/manifest.csv"
PACK_NAMES = ("data_1.pac", "data_2.pac", "data_3.pac")
CHUNK_SIZE = 1 << 20


def install_rows(root):
    def fail(error):
        raise error

    for directory, _, filenames in os.walk(root, onerror=fail):
        for filename in filenames:
            path = Path(directory) / filename
            if not path.is_file():
                continue
            digest = hashlib.sha256()
            size = 0
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(CHUNK_SIZE), b""):
                    digest.update(chunk)
                    size += len(chunk)
            yield "install", path.relative_to(root).as_posix(), size, digest.hexdigest()


def pac_rows(paths):
    archive = Archive(paths)
    try:
        for member in archive.members:
            start = member["stream_offset"]
            size = member["size"]
            pack_index = bisect_right(archive.cum, start) - 1
            origin = f"pac:{paths[pack_index].stem.lower()}"
            digest = hashlib.sha256()
            for offset in range(0, size, CHUNK_SIZE):
                digest.update(archive.read(start + offset, min(CHUNK_SIZE, size - offset)))
            yield origin, member["name"].replace("\\", "/"), size, digest.hexdigest()
    finally:
        archive.close()


def find_packs(directory):
    matches = {name: [] for name in PACK_NAMES}
    for path in directory.rglob("*"):
        if path.name.lower() in matches and path.is_file():
            matches[path.name.lower()].append(path)
    for name, paths in matches.items():
        if len(paths) != 1:
            raise ValueError(f"{directory}: expected one {name}, found {len(paths)}")
    return [matches[name][0] for name in PACK_NAMES]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pac", nargs="+", type=Path, metavar="PAC",
        help="ordered retail PAC files, overriding ROTK_ISO_DIR",
    )
    args = parser.parse_args()
    root = Path(os.environ.get("ROTK_GAME_DIR") or DEFAULT_GAME_DIR).resolve()
    destination = MANIFEST.parent.resolve() / MANIFEST.name
    try:
        if not root.is_dir():
            raise ValueError(f"game directory does not exist: {root}")
        prefix = next((path.parent for path in root.parents if path.name == "drive_c"), root)
        if destination.is_relative_to(prefix):
            raise ValueError("manifest destination is inside the game prefix")
        paths = args.pac
        if paths is None and os.environ.get("ROTK_ISO_DIR"):
            paths = find_packs(Path(os.environ["ROTK_ISO_DIR"]))
        if paths and tuple(path.name.lower() for path in paths) != PACK_NAMES[:len(paths)]:
            raise ValueError("pass PACs in order starting with data_1.pac")

        rows = list(install_rows(root))
        if paths:
            rows.extend(pac_rows(paths))
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", dir=destination.parent, encoding="utf-8", newline="", delete=False,
        ) as output:
            temporary_path = Path(output.name)
            try:
                writer = csv.writer(output, lineterminator="\n")
                writer.writerow(("origin", "path", "size", "sha256"))
                writer.writerows(sorted(rows))
                output.close()
                temporary_path.replace(destination)
            finally:
                temporary_path.unlink(missing_ok=True)
    except (OSError, PacError, ValueError) as error:
        parser.exit(1, f"corpus: {error}\n")


if __name__ == "__main__":
    main()

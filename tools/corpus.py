#!/usr/bin/env python3
"""Hash the ROTK installation, retail PAC members and disc media."""

import argparse
from bisect import bisect_right
from collections import Counter
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
MANIFEST_COLUMNS = ("origin", "path", "size", "sha256")


def hash_file(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(CHUNK_SIZE), b""):
            digest.update(chunk)
            size += len(chunk)
    return size, digest.hexdigest()


def tree_rows(root, origin):
    def fail(error):
        raise error

    for directory, _, filenames in os.walk(root, onerror=fail):
        for filename in filenames:
            path = Path(directory) / filename
            if not path.is_file():
                continue
            yield origin, path.relative_to(root).as_posix(), *hash_file(path)


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


def index_members(rows, prefix=""):
    members = {}
    for _, path, size, digest in rows:
        path = prefix + path
        key = path.casefold()
        if key in members:
            raise ValueError(f"ambiguous member paths: {members[key][0]} and {path}")
        members[key] = (path, size, digest)
    return members


def verify(install, pac, output):
    installed = index_members(row for row in install if row[1].casefold().startswith("data/"))
    archived = index_members(pac, prefix="Data/")
    counts = Counter()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("status", "path", "pac_size", "pac_sha256", "install_size", "install_sha256"))
    for key in sorted(installed.keys() | archived.keys()):
        disk = installed.get(key)
        member = archived.get(key)
        if member is None:
            status = "install-only"
        elif disk is None:
            status = "pac-only"
        elif member[1:] == disk[1:]:
            status = "match"
        else:
            status = "mismatch"
        counts[status] += 1
        writer.writerow((status, (member or disk)[0],
                         *(member or ("", "", ""))[1:], *(disk or ("", "", ""))[1:]))
    statuses = ("match", "mismatch", "pac-only", "install-only")
    print("Summary " + ", ".join(f"{status}={counts[status]}" for status in statuses), file=output)
    return int(counts["mismatch"] > 0)


def iso_volume_label(path):
    """Read the ISO 9660 volume identifier from cooked or raw Mode 1 sectors."""
    with path.open("rb") as source:
        for sector_size, payload_offset in ((2048, 0), (2352, 16)):
            offset = 16 * sector_size + payload_offset
            while True:
                source.seek(offset)
                descriptor = source.read(2048)
                if len(descriptor) != 2048 or descriptor[1:7] != b"CD001\x01":
                    break
                if descriptor[0] == 1:
                    return descriptor[40:72].decode("ascii", errors="replace").rstrip(" \0")
                if descriptor[0] == 255:
                    break
                offset += sector_size
    return ""


def disc_rows(trees, images, labels):
    for index in range(max(len(trees), len(images))):
        origin = f"disc{index + 1}"
        image = images[index] if index < len(images) else None
        label = labels[index] if labels else ""
        if image is not None:
            label = label or iso_volume_label(image)
            yield origin, "image", image.name, *hash_file(image), label
        if index < len(trees):
            root = trees[index]
            if not root.is_dir():
                raise ValueError(f"disc tree does not exist: {root}")
            for _, path, size, digest in sorted(tree_rows(root, origin)):
                yield origin, "file", path, size, digest, label


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pac", nargs="+", type=Path, metavar="PAC",
        help="ordered retail PAC files, overriding ROTK_ISO_DIR",
    )
    parser.add_argument("--verify", action="store_true", help="compare PAC members with installed Data files")
    parser.add_argument("--disc-tree", nargs="+", type=Path, default=[], metavar="ROOT",
                        help="disc filesystem roots in disc order")
    parser.add_argument("--disc-image", nargs="+", type=Path, default=[], metavar="IMAGE",
                        help="disc image files in disc order")
    parser.add_argument("--disc-label", nargs="+", default=[], metavar="LABEL",
                        help="volume labels in disc order, or empty strings to detect from ISO images")
    args = parser.parse_args()
    inventory = bool(args.disc_tree or args.disc_image)
    if args.disc_label and len(args.disc_label) != max(len(args.disc_tree), len(args.disc_image)):
        parser.error("--disc-label requires one label per disc")
    if inventory and args.pac and not args.verify:
        parser.error("--pac with disc inventory requires --verify")
    root = Path(os.environ.get("ROTK_GAME_DIR") or DEFAULT_GAME_DIR).resolve()
    destination = MANIFEST.parent.resolve() / MANIFEST.name
    try:
        if inventory:
            rows = list(disc_rows(args.disc_tree, args.disc_image, args.disc_label))
            writer = csv.writer(sys.stdout, lineterminator="\n")
            writer.writerow(("origin", "kind", *MANIFEST_COLUMNS[1:], "volume_label"))
            writer.writerows(rows)
            if not args.verify:
                return 0
        if not root.is_dir():
            raise ValueError(f"game directory does not exist: {root}")
        paths = args.pac
        if paths is None and os.environ.get("ROTK_ISO_DIR"):
            paths = find_packs(Path(os.environ["ROTK_ISO_DIR"]))
        if paths and tuple(path.name.lower() for path in paths) != PACK_NAMES[:len(paths)]:
            raise ValueError("pass PACs in order starting with data_1.pac")

        if args.verify:
            if not paths:
                raise ValueError("verification requires --pac or ROTK_ISO_DIR")
            return verify(tree_rows(root, "install"), pac_rows(paths),
                          sys.stderr if inventory else sys.stdout)

        prefix = next((path.parent for path in root.parents if path.name == "drive_c"), root)
        if destination.is_relative_to(prefix):
            raise ValueError("manifest destination is inside the game prefix")
        rows = list(tree_rows(root, "install"))
        if paths:
            rows.extend(pac_rows(paths))
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", dir=destination.parent, encoding="utf-8", newline="", delete=False,
        ) as output:
            temporary_path = Path(output.name)
            try:
                writer = csv.writer(output, lineterminator="\n")
                writer.writerow(MANIFEST_COLUMNS)
                writer.writerows(sorted(rows))
                output.close()
                temporary_path.replace(destination)
            finally:
                temporary_path.unlink(missing_ok=True)
    except (OSError, PacError, ValueError) as error:
        parser.exit(1, f"corpus: {error}\n")


if __name__ == "__main__":
    sys.exit(main())

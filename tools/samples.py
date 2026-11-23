#!/usr/bin/env python3
"""Materialise and verify the local corpus samples."""
import argparse
import csv
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import sys
import tempfile


sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus import MANIFEST, game_dir, game_prefix

REPO = Path(__file__).resolve().parents[1]
FIELDS = (
    "sample_id", "source_origin", "source_path", "sha256", "size",
    "format", "variant", "why_selected", "used_by_tests",
)


@dataclass(frozen=True)
class Sample:
    sample_id: str
    origin: str
    source: Path
    size: int
    sha256: str
    destinations: tuple


def load_manifest(path):
    samples = []
    ids = set()
    destinations = set()
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if reader.fieldnames != list(FIELDS):
            raise ValueError(f"{path}: expected columns {', '.join(FIELDS)}")
        for row in reader:
            label = f"{path}:{reader.line_num}"
            if None in row or not all(row.values()):
                raise ValueError(f"{label}: invalid number of fields or empty field")
            sample_id = row["sample_id"]
            if sample_id in ids:
                raise ValueError(f"{label}: duplicate sample_id {sample_id}")
            if row["source_origin"] not in {"install", "pac"}:
                raise ValueError(f"{label}: expected install or pac origin")
            source_path = row["source_path"]
            if (any(part in {"", ".", ".."} for part in source_path.split("/"))
                    or any(char in source_path for char in "\\:\0")):
                raise ValueError(f"{label}: invalid relative source path {source_path!r}")
            source = Path(source_path)
            if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
                raise ValueError(f"{label}: expected a lowercase SHA-256")
            if not re.fullmatch(r"[0-9]+", row["size"]):
                raise ValueError(f"{label}: expected a nonnegative size in bytes")
            if not re.fullmatch(r"[a-zA-Z0-9]+(?:[ /-][a-zA-Z0-9]+)*", row["format"]):
                raise ValueError(f"{label}: invalid format {row['format']!r}")
            folder = row["format"].lower().replace(" ", "-").replace("/", "-")
            paths = [Path(folder) / source]
            if row["used_by_tests"] == "yes":
                paths.append(Path(source.name))
            elif row["used_by_tests"] != "no":
                raise ValueError(f"{label}: expected yes or no for used_by_tests")
            for destination in paths:
                key = destination.as_posix().casefold()
                if key in destinations:
                    raise ValueError(f"{label}: duplicate destination {destination}")
                destinations.add(key)
            ids.add(sample_id)
            samples.append(Sample(sample_id, row["source_origin"], source,
                                  int(row["size"]), row["sha256"], tuple(paths)))
    if not samples:
        raise ValueError(f"{path}: no samples listed")
    return samples


def within(path, root):
    return path == root or root in path.parents


def output_path(root, relative, protected):
    path = root / relative
    parent = path.parent.resolve()
    if not within(parent, root) or path.is_symlink():
        raise ValueError(f"unsafe sample destination {path}")
    if any(within(parent, source) for source in protected):
        raise ValueError(f"sample destination is inside a source directory: {path}")
    return path


def verify(sample, stream, output=None):
    digest = hashlib.sha256()
    size = 0
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        size += len(chunk)
        if size > sample.size:
            raise ValueError(f"size mismatch (expected {sample.size} bytes)")
        digest.update(chunk)
        if output is not None:
            output.write(chunk)
    if size != sample.size:
        raise ValueError(f"size mismatch (expected {sample.size} bytes, got {size})")
    if digest.hexdigest() != sample.sha256:
        raise ValueError(f"SHA-256 mismatch (expected {sample.sha256}, got {digest.hexdigest()})")


def check_file(sample, path):
    if not path.is_file():
        raise ValueError(f"missing sample file {path}")
    with path.open("rb") as stream:
        verify(sample, stream)


def source_path(sample, roots):
    root = roots[sample.origin]
    if root is None:
        raise ValueError(f"missing pac source {sample.source} (supply an extracted tree with --pac-dir)")
    path = (root / sample.source).resolve()
    if not within(path, root):
        raise ValueError(f"source escapes {root}: {sample.source}")
    if not path.is_file():
        raise ValueError(f"missing {sample.origin} source {path}")
    return path


def copy_verified(sample, source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
            name = Path(temporary.name)
            with source.open("rb") as stream:
                verify(sample, stream, temporary)
        name.replace(destination)
    finally:
        if name is not None:
            name.unlink(missing_ok=True)


def fetch_file(sample, path, roots, canonical):
    try:
        check_file(sample, path)
        return
    except ValueError:
        source = canonical if canonical is not None else source_path(sample, roots)
    try:
        copy_verified(sample, source, path)
    except ValueError as error:
        raise ValueError(f"{source}: {error}") from error


def run(args):
    samples = load_manifest(args.manifest)
    root = args.samples_dir.resolve()
    roots = {}
    if args.command == "fetch":
        roots = {
            "install": args.game_dir.expanduser().resolve(),
            "pac": args.pac_dir.resolve() if args.pac_dir is not None else None,
        }
    protected = [game_prefix(roots["install"])] if roots else []
    if roots.get("pac") is not None:
        protected.append(roots["pac"])
    if any(within(root, path) for path in protected):
        raise ValueError(f"samples directory is inside a source directory: {root}")

    failures = 0
    for sample in samples:
        canonical = None
        for relative in sample.destinations:
            path = root / relative
            try:
                path = output_path(root, relative, protected)
                if args.command == "fetch":
                    fetch_file(sample, path, roots, canonical)
                else:
                    check_file(sample, path)
            except (OSError, ValueError, RuntimeError) as error:
                failures += 1
                print(f"samples: {sample.sample_id} ({path}): {error}", file=sys.stderr)
                if args.command == "fetch" and canonical is None:
                    break
            else:
                if canonical is None:
                    canonical = path
    if failures:
        return 1
    print(f"{args.command}: verified {len(samples)} samples under {root}")
    return 0


def refresh(selection, corpus, output):
    """Keep the curated sample choices and refresh their manifest identity."""
    with corpus.open(encoding="utf-8", newline="") as stream:
        manifest = {(row["origin"], row["path"]): row for row in csv.DictReader(stream)}
    with selection.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        origin, path = row["source_origin"], row["source_path"]
        if origin == "pac":
            matches = [entry for (source, name), entry in manifest.items()
                       if source.startswith("pac:") and name == path]
            entry = matches[0] if len(matches) == 1 else None
        else:
            entry = manifest.get((origin, path))
        if entry is None:
            raise ValueError(f"{origin}:{path} has no unique corpus manifest entry")
        row.update(sha256=entry["sha256"], size=entry["size"])
    writer = csv.DictWriter(output, FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("fetch", "check", "refresh"))
    parser.add_argument("--manifest", type=Path, default=REPO / "re/corpus/samples.csv")
    parser.add_argument("--corpus-manifest", type=Path, default=MANIFEST,
                        help="source of sizes and hashes for refresh")
    parser.add_argument("--game-dir", type=Path,
                        default=game_dir())
    parser.add_argument("--pac-dir", type=Path, help="tree of pre-extracted PAC members")
    parser.add_argument("--samples-dir", type=Path,
                        default=os.environ.get("ROTK_SAMPLES_DIR", REPO / "assets/samples"))
    args = parser.parse_args(argv)
    try:
        if args.command == "refresh":
            refresh(args.manifest, args.corpus_manifest, sys.stdout)
            return 0
        return run(args)
    except (OSError, ValueError, RuntimeError, csv.Error) as error:
        print(f"samples: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

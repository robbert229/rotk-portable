#!/usr/bin/env python3
"""Fetch and verify pinned library references without extracting them."""
import argparse
import csv
import hashlib
import os
from pathlib import Path
import re
import shutil
import tempfile
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "re/corpus/reference_sources.csv"
CACHE = ROOT / "out/refs"
MSVC = ROOT / "out/toolchain/msvc700"


def verify(path, expected):
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch for {path}: expected {expected}, got {actual}")


def fetch_archive(url, target, expected):
    if target.exists() or target.is_symlink():
        verify(target, expected)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".download-", dir=target.parent) as directory:
        staged = Path(directory) / target.name
        with urlopen(url, timeout=30) as response, staged.open("xb") as stream:
            shutil.copyfileobj(response, stream)
        verify(staged, expected)
        # Another fetch may publish while we download. Never overwrite it.
        try:
            os.link(staged, target)
        except FileExistsError:
            pass
        verify(target, expected)


def fetch(manifest, cache, toolchain=None):
    with manifest.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    pins = {}
    for row in rows:
        kind = row["kind"]
        if kind in ("retail", "unresolved"):
            continue
        name = row["path"]
        path = Path(name)
        digest = row["sha256"]
        if (not path.parts or path.is_absolute() or ".." in path.parts
                or not re.fullmatch(r"[a-f0-9]{64}", digest)):
            raise ValueError(f"invalid {kind} pin for {name}")
        if kind == "toolchain":
            if toolchain is not None:
                verify(toolchain / path, digest)
                print(f"verified {toolchain / path}")
            continue
        if kind != "archive" or len(path.parts) != 1 or not row["download_url"]:
            raise ValueError(f"invalid archive pin for {name}")
        pin = (row["download_url"], digest)
        if name in pins and pins[name] != pin:
            raise ValueError(f"conflicting archive pins for {name}")
        pins[name] = pin
    for name, (url, digest) in sorted(pins.items()):
        target = cache / name
        fetch_archive(url, target, digest)
        print(f"verified {target}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("fetch",))
    parser.add_argument("--msvc-dir", type=Path, help="verify libraries in this pinned MSVC checkout")
    args = parser.parse_args()
    toolchain = args.msvc_dir
    if toolchain is None and os.environ.get("MSVC700_DIR"):
        toolchain = Path(os.environ["MSVC700_DIR"]).expanduser()
    if toolchain is None and MSVC.is_dir():
        toolchain = MSVC
    try:
        if CACHE.resolve() != CACHE:
            raise ValueError("out/refs must be inside the repository")
        fetch(MANIFEST, CACHE, toolchain)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"refs: {exc}\n")


if __name__ == "__main__":
    main()

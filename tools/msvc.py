#!/usr/bin/env python3
"""Fetch and run the pinned MSVC 7.0 toolchain under dedicated Wine."""
import argparse
import fcntl
import hashlib
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out/toolchain"
PREFIX = OUT / "wineprefix"
URL = "https://github.com/archaic-msvc/msvc700"
REV = "97fe4cdeaeb0bb934591d4b05eb52c2e8ab3e34b"
FILES = {f"Vc7/bin/{name}" for name in ("cl.exe", "c1.dll", "c1xx.dll", "c2.dll", "link.exe")}
TOOLS = ("cl", "link", "lib")


def parse_hashes(contents):
    hashes = {}
    for line in contents.splitlines():
        digest, _, name = line.partition("  ")
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or name not in FILES or name in hashes:
            raise ValueError(f"invalid toolchain hash entry: {line}")
        hashes[name] = digest
    if hashes.keys() != FILES:
        raise ValueError("incomplete toolchain hash manifest")
    return hashes


def verify(directory):
    manifest = ROOT / "re/toolchain.sha256"
    for name, expected in parse_hashes(manifest.read_text()).items():
        actual = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"SHA-256 mismatch for {directory / name}: {actual}")
    print(f"{directory}: all five SHA-256 hashes OK", flush=True)


def wine_path(path):
    return "Z:" + os.path.abspath(path).replace("/", "\\")


# Recognize path-bearing switches before treating an argument as a file path.
PATH_OPTION = re.compile(
    r"^([/-](?:(?:out|libpath|pdb|implib|def|map|ilk|manifestfile):"
    r"|(?:Fo|Fd|Fe|Fi|Fa|Fp|Tc|Tp|FI|I)(?=[^:]*?/)|FR?(?=[^:]*?/)))(.+)$",
    re.IGNORECASE,
)


WINDOWS_PATH = re.compile(r"^(?:[A-Za-z]:|\\\\)")


def translate(arg):
    if WINDOWS_PATH.match(arg):
        return arg
    if arg.startswith("@") and len(arg) > 1:
        path = arg[1:]
        return arg if WINDOWS_PATH.match(path) else "@" + wine_path(path)
    option = PATH_OPTION.match(arg)
    if option:
        prefix, path = option.groups()
        if not WINDOWS_PATH.match(path):
            return prefix + wine_path(path)
        return arg
    if "/" in arg[1:] and not arg.startswith("-") and not re.match(r"^/[Dd][^/]*=", arg):
        return wine_path(arg)
    if arg.startswith("/") and Path(arg).exists():
        return wine_path(arg)
    return arg


def compiler_env(directory, inherited):
    env = inherited.copy()
    # Wine reserves host PATH. WINEPATH prepends entries to the Windows PATH.
    for key, paths in {
        "WINEPATH": ("Common7/IDE", "Vc7/bin", "Common7/Tools",
                     "Common7/Tools/bin/prerelease", "Common7/Tools/bin",
                     "FrameworkSDK/bin"),
        "INCLUDE": ("Vc7/ATLMFC/INCLUDE", "Vc7/include", "Vc7/PlatformSDK/include/prerelease",
                    "Vc7/PlatformSDK/include", "FrameworkSDK/include"),
        "LIB": ("Vc7/ATLMFC/LIB", "Vc7/lib", "Vc7/PlatformSDK/lib/prerelease",
                "Vc7/PlatformSDK/lib", "FrameworkSDK/lib"),
    }.items():
        entries = [wine_path(directory / part) for part in paths]
        if key == "WINEPATH":
            entries.append(r"C:\Windows\Microsoft.NET\Framework\v1.0.3705")
        if env.get(key):
            entries.append(env[key])
        env[key] = ";".join(entries)
    env.pop("WINEARCH", None)
    env.update(WINEPREFIX=str(PREFIX), WINEDEBUG="-all", WINEDLLOVERRIDES="mscoree,mshtml=")
    # Wine derives this from the runner. An inherited value may select another server.
    env.pop("WINESERVER", None)
    env.pop("WINELOADER", None)
    return env


def find_wine():
    override = os.environ.get("WINE")
    if override:
        wine = shutil.which(os.path.expanduser(override))
        if not wine:
            raise ValueError(f"WINE is not executable: {override}")
        return os.path.abspath(wine)
    wine = shutil.which("wine")
    if wine:
        return os.path.abspath(wine)
    runners = Path.home() / ".local/share/lutris/runners/wine"
    for wine in sorted(runners.glob("*/bin/wine"), reverse=True):
        if wine.is_file() and os.access(wine, os.X_OK):
            return str(wine)
    raise ValueError("Wine not found. Set WINE to a runner's bin/wine executable.")


def prefix_env(directory):
    if PREFIX.resolve() != PREFIX or PREFIX.is_symlink():
        raise ValueError(f"dedicated Wine prefix must not be redirected: {PREFIX}")
    return compiler_env(directory, os.environ)


def initialize_prefix(wine, directory):
    env = prefix_env(directory)
    # An existing prefix determines its own architecture.
    if not (PREFIX / "system.reg").is_file():
        env["WINEARCH"] = "win32"
    command = [wine, "wineboot", "--init"]
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    if result.returncode and "wow64 mode" in result.stderr.lower():
        env["WINEARCH"] = "win64"
        result = subprocess.run(command, env=env, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f"Wine prefix initialization failed: {result.stderr.strip()}")
    if not (PREFIX / "system.reg").is_file():
        raise ValueError(f"Wine did not initialize {PREFIX}")


def shim_text(script, tool):
    return f'#!/bin/sh\nexec python3 -I {shlex.quote(str(script))} {tool} "$@"\n'


def write_shims():
    directory = OUT / "bin"
    directory.mkdir(exist_ok=True)
    for tool in TOOLS:
        with tempfile.NamedTemporaryFile(mode="w", dir=directory, delete=False) as shim:
            shim.write(shim_text(Path(__file__).resolve(), tool))
        path = Path(shim.name)
        path.chmod(0o755)
        path.replace(directory / tool)


def git(directory, *args, **kwargs):
    return subprocess.run(["git", "-C", str(directory), *args], check=True, **kwargs)


def fetch(directory):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "fetch.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not directory.exists() or (directory.is_dir() and not any(directory.iterdir())):
            directory.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".msvc700-", dir=directory.parent) as temp:
                staged = Path(temp) / "checkout"
                staged.mkdir()
                git(staged, "init", "--quiet")
                git(staged, "fetch", "--depth=1", URL, REV)
                git(staged, "-c", "advice.detachedHead=false", "checkout", "--detach", REV)
                verify(staged)
                staged.rename(directory)
        else:
            if not (directory / ".git").exists():
                raise ValueError(f"expected a Git checkout at {directory}")
            head = git(directory, "rev-parse", "HEAD", capture_output=True, text=True)
            if head.stdout.strip() != REV:
                raise ValueError(f"{directory} must be checked out at {REV}")
            verify(directory)
        initialize_prefix(find_wine(), directory)
        write_shims()
        print(f"Wine prefix ready at {PREFIX}")


def run_tool(wine, directory, tool, args):
    executable = directory / "Vc7/bin" / f"{tool}.exe"
    if not executable.is_file() or not (PREFIX / "system.reg").is_file():
        raise ValueError("run make toolchain first")
    result = subprocess.run([wine, wine_path(executable), *map(translate, args)],
                            env=prefix_env(directory))
    return result.returncode if result.returncode >= 0 else 128 - result.returncode


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("fetch", "env", "doctor", *TOOLS))
    # Forward all compiler arguments verbatim, including switches beginning with '-'.
    args = parser.parse_args(argv[:1] if argv and argv[0] in TOOLS else argv)
    directory = Path(os.environ.get("MSVC700_DIR") or OUT / "msvc700").expanduser().resolve()
    try:
        if args.command == "fetch":
            if directory.is_relative_to((Path.home() / "Games").resolve()):
                raise ValueError("MSVC700_DIR must be outside ~/Games")
            prefix_env(directory)
            fetch(directory)
        elif args.command == "env":
            env = prefix_env(directory)
            for key in ("WINEPREFIX", "WINEDEBUG", "WINEDLLOVERRIDES", "WINEPATH", "INCLUDE", "LIB"):
                print(f"{key}={env[key]}")
        elif args.command == "doctor":
            verify(directory)
            wine = find_wine()
            print(f"Wine: {wine}\nPrefix: {PREFIX}", flush=True)
            subprocess.run([wine, "--version"], check=True, env=prefix_env(directory))
            return run_tool(wine, directory, "cl", ["/?"])
        else:
            return run_tool(find_wine(), directory, args.command, argv[1:])
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"msvc: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

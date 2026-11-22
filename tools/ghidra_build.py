#!/usr/bin/env python3
"""Analyze an executable in a disposable local Ghidra project."""

import argparse
import csv
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
GAME = Path.home() / (
    "Games/lord-of-the-rings-the-return-of-the-king/drive_c/Program Files (x86)/"
    "EA GAMES/LOTR The Return of the King tm"
)
GHIDRA = Path.home() / ".local/opt/ghidra/ghidra_12.1.4_PUBLIC"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("--name", help="project name (defaults to executable stem)")
    parser.add_argument("--reimport", action="store_true", help="replace the imported program")
    parser.add_argument("--symbols", type=Path, nargs="+", help="CSV inputs, defaults to re/symbols")
    parser.add_argument("--export-auto", type=Path, metavar="CSV", help="write new auto rows")
    args = parser.parse_args(argv)
    args.name = args.name or args.exe.stem
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", args.name):
        parser.error("invalid project name")
    return args


def headless_command(launcher, projects, args, run_dir, existing, digest):
    command = [str(launcher), str(projects), args.name]
    if existing and not args.reimport:
        command += ["-process", args.exe.name]
    else:
        command += ["-import", str(args.exe)]
        if args.reimport:
            command += ["-overwrite"]
    command += [
        "-scriptPath", str(ROOT / "re/ghidra"),
        "-log", str(run_dir / "application.log"),
        "-scriptlog", str(run_dir / "script.log"),
        "-postScript", "ImportSymbols.java", str(run_dir / "symbols.csv"),
        str(run_dir / "auto.txt"), digest, str(run_dir / "summary.txt"),
    ]
    if args.export_auto:
        command += [
            "-postScript", "ExportSymbols.java", str(run_dir / "symbols.csv"),
            str(run_dir / "export" / args.export_auto.name), args.export_auto.stem,
            str(run_dir / "summary.txt"),
        ]
    return command


def launch(projects, launcher, args, run_dir, existing, digest, env, **options):
    command = headless_command(launcher, projects, args, run_dir, existing, digest)
    print(f"Ghidra mode: {command[3].removeprefix('-')}", flush=True)
    result = subprocess.run(command, cwd=run_dir, env=env, **options)
    log = run_dir / "application.log"
    report = log.read_text(errors="replace") if log.is_file() else ""
    if (command[3] == "-process" and
            "Requested project program file(s) not found:" in report):
        launch(projects, launcher, args, run_dir, False, digest, env, **options)
        return
    result.check_returncode()
    if "REPORT: Save succeeded for" not in report:
        raise ValueError("Ghidra did not save the program; see its output above")


def build(args):
    args.exe = args.exe.absolute()
    if args.exe.name.startswith("-") or any(c in args.exe.name for c in "*?"):
        raise ValueError("executable basename must not be a headless option or glob")
    launcher = Path(os.environ.get("GHIDRA_HOME") or GHIDRA).expanduser().resolve()
    launcher /= "support/analyzeHeadless"
    if not launcher.is_file():
        raise ValueError(f"headless launcher not found: {launcher}")
    if args.export_auto:
        args.export_auto = args.export_auto.resolve()
        configured_game = Path(os.environ.get("ROTK_GAME_DIR") or GAME).expanduser().resolve()
        game_dirs = [GAME.parents[3], GAME.resolve(), configured_game]
        game_dirs.extend(parent.parent for parent in configured_game.parents
                         if parent.name.lower() == "drive_c")
        if (any(args.export_auto.is_relative_to(path.resolve()) for path in game_dirs)
                or args.export_auto == args.exe.resolve()
                or (args.export_auto.exists() and
                    (not args.export_auto.is_file() or args.export_auto.stat().st_nlink > 1))):
            raise ValueError("export destination must not modify game files")
        if (args.export_auto.suffix != ".csv" or args.export_auto.stem.startswith("lib_")
                or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", args.export_auto.stem)):
            raise ValueError("export filename must be a non-library module CSV")
        if args.export_auto.parent == ROOT / "re/symbols":
            raise ValueError("export candidates to a separate directory for review")
    with args.exe.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()

    projects = ROOT / "out/ghidra"
    if projects.resolve() != projects:
        raise ValueError("out/ghidra must be inside the checkout without symlinks")
    projects.mkdir(parents=True, exist_ok=True)
    symdb = [sys.executable, "-BI", str(ROOT / "tools/symdb.py")]
    paths = [path.resolve() for path in (args.symbols or sorted((ROOT / "re/symbols").glob("*.csv")))]
    if args.export_auto in paths:
        raise ValueError("export destination is a symbol input")
    with tempfile.TemporaryDirectory(prefix="run-", dir=projects) as temporary:
        run_dir = Path(temporary)
        with (run_dir / "symbols.csv").open("wb") as stream:
            subprocess.run([*symdb, "export-ghidra", *map(str, paths)], stdout=stream, check=True)
        with (run_dir / "auto.txt").open("w", encoding="ascii") as stream:
            for path in paths:
                with path.open(encoding="utf-8", newline="") as source:
                    for row in csv.DictReader(source):
                        if row["status"] == "auto":
                            print(f"{int(row['address'], 16):08X}", file=stream)

        existing = (projects / f"{args.name}.gpr").is_file()
        for transient in (run_dir / "home", run_dir / "tmp"):
            transient.mkdir()
        env = dict(os.environ, HOME=str(run_dir / "home"), TMPDIR=str(run_dir / "tmp"),
                   XDG_CONFIG_HOME=str(run_dir / "home"), XDG_CACHE_HOME=str(run_dir / "home"),
                   XDG_DATA_HOME=str(run_dir / "home"))
        # JAVA_TOOL_OPTIONS also reaches LaunchSupport, which saves the JDK selection.
        env["JAVA_TOOL_OPTIONS"] = (
            env.get("JAVA_TOOL_OPTIONS", "") +
            f' -Duser.home="{run_dir / "home"}" -Djava.io.tmpdir="{run_dir / "tmp"}"'
        )
        (run_dir / "export").mkdir()
        # Ghidra rejects hidden project path components (such as .t3).
        # A directory descriptor gives it a visible Linux path to the same directory.
        if any(part.startswith(".") for part in projects.parts):
            project_fd = os.open(projects, os.O_RDONLY | os.O_DIRECTORY)
            try:
                launch(Path(f"/proc/self/fd/{project_fd}"), launcher, args, run_dir,
                       existing, digest, env, pass_fds=(project_fd,))
            finally:
                os.close(project_fd)
        else:
            launch(projects, launcher, args, run_dir, existing, digest, env)
        summary = run_dir / "summary.txt"
        if not summary.is_file():
            raise ValueError("Ghidra did not finish symbol import; see its output above")
        if args.export_auto:
            exported = run_dir / "export" / args.export_auto.name
            subprocess.run([*symdb, "lint", *map(str, paths), str(exported)], check=True)
            shutil.copyfile(exported, args.export_auto)
        print(summary.read_text().strip())


def main():
    try:
        build(parse_args())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"ghidra_build: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

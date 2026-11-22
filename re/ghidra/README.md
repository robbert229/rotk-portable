# Headless Ghidra pipeline

Use Ghidra 12.1.4 and a JDK 21 or newer. Set `JAVA_HOME` if the JDK
is outside `PATH`. The wrapper uses
`~/.local/opt/ghidra/ghidra_12.1.4_PUBLIC` unless `GHIDRA_HOME` is set.
The scripts use Ghidra's bundled Java scripting support.

```sh
make ghidra
make ghidra EXE=out/unpacked/ROTK_unpacked.exe
make ghidra-export GHIDRA_EXPORT=out/ghidra/unassigned.csv
ROTK_GHIDRA_IT=1 make test
```

`EXE` defaults to `ROTK_UNPACKED_EXE` when set and to the packed retail
executable under `ROTK_GAME_DIR` otherwise. The integration test reads
`eauninstall.exe` from that game directory and uses a synthetic symbol
fixture for its retail PE entry point. Ordinary `make test` skips it.

The project lives at `out/ghidra/<executable-stem>.gpr` with its database alongside it.
A repeat run processes the existing
program and reapplies the CSVs. Use `--reimport` to replace the program
when its bytes change, or `--name` for another project. To discard local
edits and restart for the same executable, run:

```sh
python3 -BI tools/ghidra_build.py "/path/to/ROTK.exe" --reimport
```

On Linux, checkouts under a hidden directory such as `.t3` use a
`/proc/self/fd` alias because Ghidra rejects hidden project path
components. The alias points to the existing output directory.

## Symbol round trip

The wrapper validates the selected source CSVs through
`symdb.py export-ghidra`. `ImportSymbols.java` consumes the five-column
export and gets the auto-row addresses separately because the export
omits status. Use `--symbols module.csv ...` to select an image-specific
set. Keep packed and helper PE rows separate from the repaired ROTK
database. The project input hash guards against reusing a project for
different bytes. Match the CSVs to the image yourself.

The importer creates or renames functions and sets known sizes as
contiguous function bodies. It creates primary labels for data and
vtables, and uses known sizes or resolvable declarations to define data
where the listing permits. Empty signatures preserve existing types.
An auto row cannot replace a user-defined symbol. The summary counts
successful rows, including rows already applied. A conflict names the
row and reason. Inspect and reconcile the rows before using the project
for further analysis. A conflicting row can leave earlier edits from
that row in the disposable project.

With `--export-auto path/module.csv`, the exporter emits function entries
outside the source database's occupied ranges. It uses `FUN_xxxxxxxx`,
the destination filename stem as module, an empty unit and signature,
and size `0x0` because a Ghidra body may be discontiguous. The wrapper
lints the candidates together with the source files before copying them
to the requested destination. Review candidates before adding them to
the database. The wrapper leaves the source CSVs intact.

## Limits and observed results

The importer uses Ghidra's C parser and the program's available types.
Declarations requiring repository headers or types absent from the
project may conflict. Function sizes that cut an instruction or
overlap another function require review. Existing incompatible data
definitions also require review.

[observed: Ghidra 12.1.4, packed ROTK.exe SHA-256
95af128c93c63fe5d847609b45f3ba146af56f01c76215389bd1aabf0eb2a5a2]
Both the initial import and the repeat process run reported 48 functions,
zero symbols applied and zero conflicts with the empty database.

The launcher runs with its working directory, home, caches, logs and
temporary files under `out/ghidra/`. The executable is opened for reading
and passed as an import input. The optional export path must be outside
the game installation and separate from the source database.

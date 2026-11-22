# Symbol database schema v1

The CSVs are the source of truth for symbols. Rebuild Ghidra labels and
signatures from these files alongside the types and unit map (D-5).
This document defines the contract. Assertions about the game in symbol
records use the evidence tags below.

## Source files

Use UTF-8 CSV with this exact header:

```csv
address,size,name,unit,module,kind,signature,status,evidence
```

Use one physical line per entry, trimmed fields, and standard CSV escaping
(double embedded quotes inside quoted fields). The canonical form uses LF,
minimal quoting, and ascending numeric addresses.

| Field | Contract |
| --- | --- |
| address | Hex VA in the repaired unpacked ROTK.exe, based at `0x400000`. Use a lowercase `0x` prefix and up to eight hex digits. Canonical form pads to eight uppercase digits. |
| size | Hex byte count with the same prefix and digit rules. Canonical form uses uppercase digits without padding. `0x0` means unknown and reserves the entry address for lint. Nonzero ranges are half-open and may abut. |
| name | ASCII C identifier. See naming rules below. |
| unit | Extensionless, slash-separated path beginning with `module/`, so `src/<unit>.c` is the corresponding source path. May be empty at `auto`. WP-2.3 should use the same qualified IDs in its unit map. |
| module | Exact CSV filename stem, case-sensitive. Each module and unit path component starts with a letter or underscore and continues with letters, digits, underscores or hyphens (ASCII). |
| kind | `func`, `data`, `vtable`, or `lib`. The `lib` kind denotes statically linked library functions and is exclusive to `lib_*.csv`. |
| signature | C declaration without a trailing semicolon. Include the symbol identifier and, for functions, a complete prototype with the recovered calling convention. Data and vtable signatures describe the object declaration. May be empty at `auto` or `named`. Consumers resolve types using the repository type headers. |
| status | One state from the table below. |
| evidence | One or more playbook §4 tags separated by spaces. May be empty at `auto`. |

Prefer a recovered original name backed by asserts, logs or source paths.
Use `<Module>_<Verb><Noun>` for descriptive function names, or
`<Unit>_<name>` for statics confined to one unit. Use identifier-safe
prefixes for paths with punctuation. Preserve original library identifiers.
Use `<Type>_vtbl` for tables, `<Type>_<method>` for slots, and PascalCase
for struct types. Use `unk_<hexoffset>` for unknown fields and
`pad_<hexoffset>` for padding. Only auto functions may use `FUN_` followed
by eight uppercase digits encoding their VA. Lint checks syntax and
structural relationships. Review checks naming provenance and declarations.

| Status | Meaning |
| --- | --- |
| auto | Analysis produced an entry that awaits review. |
| named | Evidence supports the name. |
| typed | Evidence supports the declaration and any recovered calling convention. |
| decomp | Reconstructed function passed D-1 byte comparison with the pinned matching toolchain and project flags. |
| verified | A second independent source corroborates the reconstruction and the D-1 comparison passed. |
| nonmatching | Reconstructed function has a documented byte mismatch, a source `NONMATCHING` reason, and a passing equivalence test under D-1. This state makes the exception visible in progress reporting. |

For evidence, use `[observed: source and finding]`,
`[inferred: reasoning and anchors]`, or `[unknown: unresolved detail]`.
Include locators such as the image VA or file offset, and identify the repaired
image by SHA-256 in the supporting document header. Cite the match report
for `decomp` and `verified`, the corroboration for `verified`, and the
reason and passing equivalence test for `nonmatching`. Lint validates tag
syntax. Review verifies provenance and test results.

## Ownership and image scope

One agent owns each `re/symbols/<module>.csv` or `re/symbols/lib_<library>.csv`.
Commit each symbol once under the owning module and coordinate ownership
transfers before moving rows. Run lint over the full directory after bringing
branches together. Address ranges are exclusive across files, including
library files. Keep one canonical row for a shared address.

V1 covers only repaired ROTK.exe VAs. DivX DLLs, the packed executable, and
helper images have independent address spaces. If they need databases, use
separate per-image directories with their own base and image identity, and
version the importer before adding those inputs.

## Commands and exports

`make lint` validates the repository, including an empty symbol directory.
`make test` runs lint and the regression suite. Every subcommand defaults to
all repository symbol CSVs. Explicit file arguments select the entire input
set for that invocation, including cross-file range checks. Run default lint
before landing any change.

`merge` validates the entire selection before canonicalizing each file in
place. It preserves module boundaries and rejects conflicting ranges.
`stats` reports each status as a percentage of rows in its module, with a
row-weighted total across all modules. An empty input reports zero percentages.

Both stdout exports use CSV with LF, minimal quoting, canonical hex, and
ascending VA order. Redirect them to a generated file under `out/`.

- `export-ghidra` v1 header is `address,size,name,kind,signature`. Use size
  as a byte length when known. Use kind to distinguish functions and library
  functions from data and vtables. An empty signature leaves the current type
  intact. Apply only to the repaired image used to author the rows. Preserve
  evidence, unit and status in the source CSVs when refreshing auto entries.
- `export-hooks` v1 header is
  `address,name,signature,enabled_by_default`. Includes reconstructed
  functions (`decomp`, `verified`, `nonmatching`). The last field is the
  literal `false` for every candidate. WP-5.1 resolves replacement symbols
  against the build and controls enablement through its runtime configuration.

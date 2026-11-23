# Installed-file references

[observed: the baseline is the 120 install rows in the
[corpus manifest](../../re/corpus/manifest.csv). Packed ROTK.exe SHA-256 is
`95af128c93c63fe5d847609b45f3ba146af56f01c76215389bd1aabf0eb2a5a2`.
The manifest identifies the companion DLLs by hash.]

## Reproduce

Run `make filerefs` with `ROTK_GAME_DIR` set to the retail directory or use
the default in the [playbook](../agent-playbook.md). The command writes the
[binary references](../../re/corpus/filerefs.csv) and
[listing entries](../../re/corpus/listed_files.csv).

The binary scan checks NUL-terminated printable ASCII and ASCII-range UTF-16LE
in the packed EXE and installed DLLs. Offsets are hexadecimal file offsets.
The filter accepts filename-shaped strings with known extensions, qualified
paths with other extensions, and recognizable directory and format strings.
It retains qualified build paths, which are also covered by the
[source-path inventory](../../re/strings/source_paths.txt).
Diagnostic sentences, runtime-assembled names and non-ASCII names are outside
the scan.

Comparison folds case, normalises separators and removes dot segments. A bare
binary filename can match any installed basename. Relative binary paths can
match under the install root or `Data/`. Listing paths are install-relative.
Patterns are lexical. A printf field matches within one path component, and
a stand-alone extension matches any basename with that suffix. `resolves_to`
lists install spellings separated by `|`. A `listed:` item records a matching
listing name without an installed counterpart. `pattern-matches-N` counts
installed matches.

The listing CSV preserves physical line numbers and the installer type code
where present. Path-only entries have type `file`, `directory` or `pattern`.
Byte sizes are blank where the listing supplies none. For the wildcard row,
`present_in_install=yes` means at least one installed file matches.

## Binary references without an installed counterpart

[observed: the binary CSV records 142 hits, comprising 123 literals, 14
patterns and five directories. Packed ROTK.exe contributes 114 hits from
`.rdata` and `stxt371`. The five DLLs contribute 28 hits, including a
UTF-16LE `eax.dll` hit in `.rsrc` at file+0x1F2A4.]

| Reference | Evidence and interpretation |
| --- | --- |
| `data\movies\blakfmv1.vid` | [observed: ROTK.exe .rdata file+0x1464E0. The path is absent from the install and both installed lists.] [unknown: whether it refers to omitted content, another build or a runtime alias.] |
| `Data/Game/San` | [observed: ROTK.exe .rdata file+0x13BFD8. The path and any subtree are absent from the install and lists.] [inferred: a directory candidate based on its spelling and the adjacent installed `Data/Game/Fro` at file+0x13BFE8.] |
| `\ROTK.ini`, `\rotkgame1.sav`, `\rotkgame2.sav` | [observed: ROTK.exe .rdata file+0x139D60, file+0x13CB6C and file+0x13CB5C respectively. All are absent from the install and lists.] [inferred: configuration and save paths based on the suffixes.] |
| `%s\Tess_Send.txt` and five related send/receive patterns | [observed: ROTK.exe .rdata file+0x13E588 through file+0x13E5E0. All six have zero lexical matches.] [unknown: the substituted runtime directory and whether these paths are read or written.] |
| `ROTK_EN_Fin_Win_DotNet.exe` and qualified source paths | [observed: the EXE name at ROTK.exe .rdata file+0x159740 and the qualified source paths in the binary CSV are absent from the install.] [inferred: build-time identities.] |
| Windows DLL names and `CdaC15BA.SYS` | [observed: the bootstrap DLL names at ROTK.exe file+0x19F01C through file+0x19F092 and the driver name at DrvMgt.dll .data file+0x685C have no install matches.] [inferred: platform or driver references based on their names and location.] |

[observed: the [PAC spec](../formats/pac.md#toc-logical-stream-of-data_1-only)
records 99 TOC entries, including 16 directories and 83 files verified against
the installed `Data/` payload. The missing video and directory are absent from
the installed payload.]
[unknown: whether either occurs elsewhere on the discs or in another build.]

## Listing coverage and unnamed installed files

- [observed: all 87 `manifest.txt` entries resolve, including all 83 files
  under `Data/`. Of 21 `filelist.txt` entries, 14 resolve. These include
  the `Support\*.*` wildcard, which covers 22 installed files. The lists
  name 96 distinct installed files explicitly and cover 118 with the wildcard.]
- [observed: seven `filelist.txt` entries are absent. Lines 1 and 2 name
  `cache.dat` and `C_TMP00_.DAT`. Lines 12, 14 and 15 name `data_1.pac`,
  `data_2.pac` and `data_3.pac`. Lines 16 and 17 name `00000001.TMP` and
  `00000002.TMP`.] [inferred: the DAT and TMP names suggest working files.
  The [PAC spec](../formats/pac.md) identifies the three PAC names as disc
  archives expanded into the install.]
- [observed: `common_filelist.txt` is absent from the install manifest.
  `Input.ini` has zero path-valued assignments under the scan filter.
  Its line 3 mentions `Input.ini` in a comment. The listing rows carry no byte sizes.]
- [observed: the packed binaries explicitly name nine distinct installed files.
  Of the remaining 111, 87 have a literal listing and 24 lack a literal in
  either source. Those 24 are the 22 `Support/` files and the two listing
  files themselves. The listing files match the DivxMediaLib.dll `.txt`
  suffix at file+0xF3B0, so every installed file has at least a literal or
  pattern match across the two CSVs.]
- [observed: the two explicit `Data/` literals that resolve are
  `Data/Game/GlobScen.scw` and `Data/LoadOnce.scw` at ROTK.exe file+0x13BFF8
  and file+0x13C010. The other 81 data files have listing entries. The
  `.scw` and `.avi` suffixes at file+0x139ACC and file+0x1466B0 match 44
  scene files and 37 movies.] [unknown: which paths the game opens at runtime.]

## Rerun after M1

[inferred: protected raw sections can hide file references, based on the
[packed section map](../research/safe-disc.md#packed-section-map). The binary
missing set, pattern matches and installed-file coverage are provisional
until the repaired dump can be scanned.]

With a validated M1 image, regenerate alongside the packed baseline:

```sh
python3 -I tools/filerefs.py \
  --exe "${ROTK_UNPACKED_EXE:-out/unpacked/ROTK_unpacked.exe}" \
  --output-dir out/filerefs-m1
```

Compare the binary CSVs by normalised path and source. Offsets are specific
to each image. Recompute the unmatched binary names, pattern matches and
installed files without a literal. Use code references to check the candidate
video and directory names and distinguish runtime-generated files from
required inputs. The listing-versus-install comparison is independent of M1.

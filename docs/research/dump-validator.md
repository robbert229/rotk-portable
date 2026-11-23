# WP-1.3b dump validator

Run `make validate-dump` for the M1 gate after WP-1.5 repair. For raw
WP-1.4 Scylla output, use `make validate-dump VALIDATE_FLAGS=--pre-repair`.
Both commands read `ROTK_UNPACKED_EXE`, which defaults to
`out/unpacked/ROTK_unpacked.exe`. The positional CLI is
`python3 -I tools/validate_dump.py [--pre-repair | --structural] FILE`.
`--structural` checks generic PE structure. The sorted JSON report's
top-level `ok` determines the exit status.
[observed: validator CLI and Makefile.]

- [observed: `objdump -p "$d/ROTK.exe"`, using the playbook installation
  directory for `d`, lists both `KERNEL32.dll` and `USER32.DLL` as static
  bootstrap import descriptors. See the [packed section map](safe-disc.md#packed-section-map).]
  [inferred: require both in the rebuilt import table as a minimum sanity check.]
- [observed: packed ROTK.exe, `strings -at x` file offsets: `eax.dll` at
  0x138778, `d3d8.dll` at 0x14B3C0, `DINPUT8.dll` at 0x14BB30,
  `DivxMediaLib.dll` at 0x1582F0 and `DSOUND.dll` at 0x158310.]
  [unknown: whether the rebuilt import table contains these DLLs.]
  [inferred: the name strings support advisory checks only. DivxMediaLib
  may be resolved at runtime, as discussed in the [FMV analysis](../analysis/fmv-pipeline.md).]
  [observed: validator reports absent advisory DLLs in `imports.advisory_missing`.]
- [observed: WP-1.1 measured packed .text entropy at 7.9987 bits per byte
  over raw bytes, including padding.]
  [inferred: require entropy below 7.5 bits per byte to flag near-uniform content.]
- [observed: the 2,874,232-byte reference is recorded in the
  [PCGamingWiki findings](safe-disc.md#pcgamingwiki-game-page). The local packed
  ROTK.exe is 2,874,240 bytes, eight bytes larger.]
  [observed: `file_size` is advisory and reports actual bytes, reference bytes
  and signed delta in bytes.]
- [observed: the WP-1.1 map identifies `stxt371`, `stxt774` and the
  eight-space section name. The validator scans file-backed mapped
  `.text` for E8/E9 rel32 and FF 15/FF 25 absolute PE32 operands. The latter
  must address an aligned slot from the IAT directory or terminated import
  thunk tables. Every reported target must land within a named SafeDisc
  section. The JSON includes counts and the first 32 matches in source
  order, each with source RVA, kind, target RVA and target section.
  Default mode fails on any match. `--pre-repair` leaves all other ROTK
  checks in force and reports matches without failing on them.]
- [inferred: the byte scan can mistake instruction operands or embedded
  data for opcodes at non-instruction offsets. Confirm reported matches
  during repair, and use disassembly to check live references outside
  the supported encodings.] [unknown: verified data ranges in the
  unpacked `.text` and behavior against the first reconstructed dump.]

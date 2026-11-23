# WP-1.3 dump validator

Run `make validate-dump` from the repo root. It reads
`ROTK_UNPACKED_EXE`, defaulting to `out/unpacked/ROTK_unpacked.exe`.
For a generic PE, run `python3 -I tools/validate_dump.py --structural FILE`.
The JSON report's top-level `ok` also determines the exit status.

- [observed: packed ROTK.exe, file offsets from `strings -at x`:
  `eax.dll` at 0x138778, `d3d8.dll` at 0x14B3C0, `DINPUT8.dll` at
  0x14BB30, `DivxMediaLib.dll` at 0x1582F0 and `DSOUND.dll` at
  0x158310. The packed bootstrap import table also names `kernel32.dll`
  and `user32.dll`; see the [section map](safe-disc.md#packed-section-map).]
- [inferred: the seven DLLs are the requested minimum candidate import set,
  matched case-insensitively. The [FMV analysis](../analysis/fmv-pipeline.md)
  suggests DivxMediaLib is late-bound, so the strict check may flag a valid dump.]
  [unknown: complete rebuilt import set and which names will be statically imported.]
- [observed: the packed .text entropy is 7.9987 bits per byte over its raw
  bytes, including alignment padding.] [inferred: require entropy strictly
  below 7.5 bits per byte using the same raw-range convention to flag
  near-uniform content.]
- [observed: the 2,874,232-byte reference is recorded in the
  [PCGamingWiki findings](safe-disc.md#pcgamingwiki-game-page).]
  [inferred: allow ±512 KiB for padding, retained sections and import rebuilding.
  Size alone has little discriminating power; retail is only eight bytes larger.]
- [observed: the WP-1.1 map identifies `stxt371`, `stxt774` and an
  eight-space name.] [inferred: scan file-backed mapped .text for E8/E9
  rel32 and FF 15/FF 25 absolute PE32 operands that address an IAT slot
  whose stored VA points into one of those sections. IAT slots come from the
  IAT directory or import descriptors and their terminated thunk tables.
  The byte scan can match instruction operands or data. Counts are advisory
  so residual references can be investigated in WP-1.5.]
- [unknown: thresholds and import assumptions against the first local
  reconstructed dump. A passing report establishes suitability for further
  inspection and leaves runtime behavior to later work packages.]

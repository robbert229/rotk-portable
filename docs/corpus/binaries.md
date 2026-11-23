# Retail PE catalogue

[observed: the retail install in [manifest.csv](../../re/corpus/manifest.csv)
contains 15 PE images, all PE32 x86. Six are under `Support/`. The
signature scan found no PE with an extension other than `.exe`, `.dll`
or `.sys`. ROTK.exe SHA-256 is
`95af128c93c63fe5d847609b45f3ba146af56f01c76215389bd1aabf0eb2a5a2`.]

Run `make pecat` to regenerate the catalogue. Override `ROTK_GAME_DIR` to
select the install. Run `python3 -I tools/pecat.py --output-dir PATH` to
write a comparison copy.

[observed: [binaries.csv](../../re/corpus/binaries.csv) records headers,
directories and derived file facts.
[pe_sections.csv](../../re/corpus/pe_sections.csv) records the 66 section
headers in zero-based table order. Its `va` column holds the section
RVA. The entropy is Shannon bits per byte across each raw range,
including file padding. Section names use `\xNN` for spaces,
non-printable bytes and literal backslashes, with trailing NUL padding
omitted. [pe_imports.csv](../../re/corpus/pe_imports.csv) records 2,019
on-disk import thunks, including delay-load entries. An ordinal is
written as `#` followed by its decimal number.]

[observed: list cells use `;`, with literal percent signs and
semicolons encoded as `%25` and `%3B`. DLL labels and counts align by
position, as do the CodeView columns. Debug directory items are
`type@file_offset/size`. NB10 supplies a PDB timestamp in place of a
GUID. Version fields preserve distinct string-table values in resource
order. Resource type counts count language leaves per numeric type or
`name:` label. The export count is the declared number of address table
slots. The overlay spans all bytes after the headers and file-backed
sections, including any debug payload there.]
[Microsoft PE format](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format) ·
[Version resource strings](https://learn.microsoft.com/en-us/windows/win32/menurc/string-str)

## Binaries

[observed: linker stamps are from each PE optional header. Build numbers
are from the corresponding Rich records. Role inferences use the
[README](../../README.md), [companion DLL dossiers](../analysis/companion-dlls.md),
[SafeDisc research](../research/safe-disc.md) and
[support-file inventory](../formats/misc.md).]

| Binary | Role | Toolchain | Notable findings |
| --- | --- | --- | --- |
| `DivxDecoder.dll` | [inferred: DivX video decoder, from the dossier's codec API analysis.] | [observed: linker 6.00, Linker600 build 8447.] | [observed: 4 export slots and 60 KERNEL32 imports.] |
| `DivxMediaLib.dll` | [inferred: FMV playback controller, from the dossier's import graph.] | [observed: linker 6.00, Linker600 build 8447.] | [observed: 22 export slots, 12 FileParser imports and 4 DivxDecoder imports.] |
| `DrvMgt.dll` | [inferred: SafeDisc driver manager, from the README and the driver-name strings in the SafeDisc research.] | [observed: linker 6.00, Linker600 build 8447.] | [observed: 3 export slots and an empty resource directory.] [unknown: driver-manager build.] |
| `FileParser.dll` | [inferred: AVI splitter and frame-buffer manager, from the dossier's AVI diagnostics and export names.] | [observed: linker 6.00, Linker600 build 8447.] | [observed: 16 export slots and 68 KERNEL32 imports.] |
| `ROTK.exe` | [observed: the retail game executable identified by the README hash.] | [observed: linker 7.00, Linker700 build 9466 and Utc13_C build 9466.] | [observed: 8 sections, entry RVA `0x5c305e` in `stxt371`, valid Rich checksum, RSDS age 47 and a 1,170,304-byte overlay. The on-disk PE checksum differs from the recomputed checksum.] |
| `SECDRV.SYS` | [observed: Macrovision SECURITY Driver, from RT_VERSION.] | [observed: linker stamp 5.10, CVTRES build 1668.] [unknown: exact linker build.] | [observed: native subsystem, `INIT` entry section, FileVersion string `3.19.000` and matching stored/computed PE checksum `0xdefc`. Its Rich checksum matches the record-only calculation.] |
| `Support/EReg.exe` | [inferred: EA Registration client, from the EReg resource strings and the support-file inventory.] | [observed: linker 6.00, with VC6-era Rich records.] | [observed: version `1, 0, 0, 54` and a WININET import.] |
| `Support/EasyInfo.exe` | [inferred: support diagnostics, from the EasyInfo PDB path, media API imports and the support-file inventory.] | [observed: linker 7.00, Linker700 build 9466.] | [observed: RSDS age 1 and DDRAW and DSOUND imports.] |
| `Support/LOTR The Return of the King tm_EZ.exe` | [inferred: EA system-information utility, from ProductName.] | [observed: linker 7.00, Linker700 build 9466.] | [observed: FileDescription `Easy MFC Application`, version `2, 1, 0, 5` and 21 WSOCK32 imports.] |
| `Support/LOTR The Return of the King tm_code.exe` | [inferred: CD-key utility, from the version resource and PDB name.] | [observed: linker 7.00, Linker700 build 9466.] | [observed: FileDescription `CDKey`, version `1.2.0.117` and a different SHA-256 from the same-sized `eauninstall.exe`.] |
| `Support/LOTR The Return of the King tm_uninst.exe` | [observed: `Ereg registry key remover` in FileDescription.] | [observed: linker 6.00, with VC6-era Rich records.] | [observed: original filename `unins_eReg.exe` and four ADVAPI32 imports.] |
| `Support/go_ez.exe` | [inferred: Get Online Easy launcher, from the support-file inventory.] | [observed: linker 6.00, with Linker620 build 8755 records.] | [observed: 39 KERNEL32 imports, including `CreateProcessA`.] |
| `eauninstall.exe` | [observed: EA Uninstall in ProductName.] | [observed: linker 7.00, Linker700 build 9466.] | [observed: version `1.2.0.189` and PDB basename `eauninstall7.pdb`.] |
| `eax.dll` | [inferred: Creative EAX audio wrapper, from the README's API evidence and the EAX Unified version strings.] | [observed: linker 6.00, Linker600 build 8447 and two VS .NET 2003-era Rich product IDs.] | [observed: version `3.066` and 7 export slots.] |
| `rotk_uninst.exe` | [inferred: game-specific PCExtras uninstaller, from the RSDS path.] | [observed: linker 7.00, Linker700 build 9466.] | [observed: RSDS age 25 and PDB basename `rotk_uninst.pdb`.] |

## Cross-checks

- [observed: the README's ROTK.exe hash, linker stamp, PDB path, GUID and
  age agree with the catalogue. Its SafeDisc paragraph describes scrambled
  OS and subsystem fields and includes a `tdb` section. The retail optional
  header contains OS version 4.0, subsystem version 4.0 and subsystem 2
  (Windows GUI). The eight section headers include neither a `tdb` entry
  nor a section beyond `stxt371`. These readings agree with the later
  SafeDisc static fingerprint.]
- [observed: the DivX DLL hashes, image bases, linker stamps, timestamps,
  export counts and DivxMediaLib import counts agree with the companion
  dossiers. The dossiers list a fifth section called `tdb` for all three.
  The section tables at file+0x1e8 in DivxDecoder and file+0x1e0 in
  DivxMediaLib and FileParser each list four sections, `.text`, `.rdata`,
  `.data` and `.reloc`. No section named `tdb` appears in any of the
  15 images.] [unknown: the source of the earlier `tdb` section claim.]
- [observed: ROTK.exe directory 1 points into `stxt371` and lists 10
  bootstrap imports across six DLLs, matching the SafeDisc static
  fingerprint. Directory 13 at file+0x1585a0 separately lists 21 delay-load
  imports across five DLLs, including 12 from `DivxMediaLib.dll`.
  Neither `FileParser.dll` nor `DivxDecoder.dll` appears in these two
  directories. `DivxNextAudioChunk`, a tentative identification in the
  dossier's ROTK.exe strings, is absent from the visible import names.]
  [unknown: additional runtime-resolved APIs.]
- [observed: the SafeDisc packed-section table puts the start of the
  resource directory in `.data1`. Directory 2 instead gives RVA
  `0x5a2000`, the start of `.rsrc` at file+0x17a000. The table starts
  with three resource types, IDs 3, 6 and 14. The preceding `.data1`
  section starts at RVA `0x5a1000`.]

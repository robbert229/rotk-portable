# MSVC 7.0 setup and ROTK flag hypothesis

## Setup

[observed: `make toolchain` shallow-fetches
`97fe4cdeaeb0bb934591d4b05eb52c2e8ab3e34b` from
[archaic-msvc/msvc700](https://github.com/archaic-msvc/msvc700). A repeat
checks HEAD and verifies all five digests in `re/toolchain.sha256` without
contacting the remote. Adding one byte to `Vc7/bin/c1.dll` made fetch fail
with `SHA-256 mismatch` before Wine startup. Restoring the file cleared
the error.]

```sh
make toolchain
make doctor
make hello
ROTK_MSVC_IT=1 make test
```

[observed: `tools/msvc.py` defaults to `out/toolchain/msvc700`. Set
`MSVC700_DIR` to fetch into another directory or reuse a checkout at the
pinned revision. Keep it outside the game directory and out of Git.
Set `WINE` to an executable path or command name to override discovery.
Discovery checks PATH first, then executable Lutris `*/bin/wine` runners
under `~/.local/share/lutris/runners/wine/` in descending directory-name order.
Use a runner that can execute 32-bit Windows programs.]

[observed: the local Lutris `wine-staging-11.2-x86_64` runner used a win64
prefix after rejecting win32 in WoW64 mode. The wrapper tries win32 for a
new prefix and retries in win64 on the WoW64 architecture error. It reuses
the prefix architecture on subsequent runs. The managed prefix lives at
`out/toolchain/wineprefix` and overrides inherited `WINEPREFIX` and
`WINEARCH`. `WINEDEBUG=-all` silences Wine tracing and the mscoree/mshtml
overrides suppress Mono and Gecko prompts. A runner change that requires a
different prefix architecture needs a fresh dedicated prefix.]

[observed: the wrapper derives the compiler search paths from the pinned
`Common7/Tools/vsvars32.bat`. Wine receives Windows PATH additions through
`WINEPATH` and Windows-format `INCLUDE` and `LIB` lists. Inspect them with
`python3 -I tools/msvc.py env`. Fetch generates executable `cl`, `link`,
and `lib` shims under `out/toolchain/bin`. Regenerate them after moving the
worktree. The wrapper translates command-line file paths and common
path-bearing switches to Wine's `Z:\` drive. It translates an `@response`
file's name. Supply Windows-compatible paths inside response files.]

[observed: `make doctor` reports wine-11.2 (Staging) and cl
`13.00.9466 for 80x86`. `make hello` links the smoke executable and
verifies `hello.obj` has absolute `@comp.id` value `0x001c24fa`
(Utc13_C, prodid 28, build 9466). The linked PE has valid Rich records
for Utc13_C and Linker700 (prodids 28 and 61, both build 9466).]

### Include dependency scanning

[observed: `make hello` compiles with `/showIncludes` and cl 13.00.9466
emits `Note: including file:` followed by the Wine path to
`Vc7\include\stdio.h`. Compilation exits zero. The flag is also listed
in the help output.]

[inferred: WP-5.0 can start with Ninja's MSVC include scanner. Verify
that it maps Wine's emitted paths to the Linux files and rebuilds when
an included header changes.] [unknown: CMake compiler detection and Ninja
dependency tracking through these shims.]

## Candidate release flags

[observed: the [Rich-header study](toolchain.md) identifies VC7 RTM C
objects in the retail image. The project README records static CRT
startup evidence. The pinned compiler's `/?` lists `/O1`, `/O2`, `/Oy[-]`,
`/G6`, `/Gd`, `/Gr`, `/Zp[n]`, `/GS` and `/MT`. `/G7` is absent
from that help output.]

| Flag | Working hypothesis |
| --- | --- |
| `/O2` vs `/O1` | [inferred: begin with speed optimization for the release engine. Compare size optimization on loops and call-heavy functions where code generation can distinguish the settings.] |
| `/Oy` | [inferred: start with frame-pointer omission under optimization. Compare `/Oy-` on ordinary non-leaf functions, and account for functions that require a frame regardless.] |
| `/G6` vs `/G7` | [inferred: use the advertised `/G6` tuning for the first pass. Probe whether `/G7` is recognized before adding it to the matrix.] |
| `/Gr` vs `/Gd` | [inferred: start with `/Gd` for C. Check stack cleanup and ECX/EDX argument use at call sites before testing global fastcall or per-function conventions.] |
| `/Zp` | [inferred: start with compiler-default packing. Use member offsets and array strides to test other packing and check for local overrides.] |
| `/GS` | [inferred: probe both settings. Use functions with eligible stack buffers and look for cookie loads and checks to establish whether it was enabled.] |
| `/MT` | [inferred: start with the static multithreaded CRT, `LIBCMT.LIB`. Identify CRT members in the repaired executable to distinguish CRT options and any explicit linker selection.] |

[unknown: the original flags and their variation by translation unit.]

### Confirmation after M1

[inferred: select roughly ten small functions from several source units
with reliable boundaries and prototypes. Include leaf and non-leaf
functions, loops, calls, struct accesses, and an eligible stack-buffer
function. Rebuild from the baseline with one option changed at a time.
Use original virtual addresses and recompiled symbols to align functions.
Compare raw bytes with a recorded mask for relocations, external branch
displacements and absolute addresses. Record the repaired image digest,
compiler build, exact flags, addresses, compared byte counts and any
remaining mismatches. Use the whole sample to check a candidate and
record any per-unit exceptions or flags the sample cannot distinguish.]

## WP-5.2 comparison tooling

- [observed: isledecomp's reccmp documents comparing an original binary
  against a recompiled executable and its PDB. Source annotations identify
  original addresses. This fits a stripped original and a fresh build
  with symbols. The interface operates on linked images.]
  [reccmp README](https://github.com/isledecomp/reccmp#available-tools)
- [observed: objdiff documents x86 support and compares pairs of
  relocatable objects. Its reader handles COFF sections and relocations,
  providing a path for VC7 object comparisons when both sides are
  available as objects. The documented workflow uses object symbols.]
  [objdiff README](https://github.com/encounter/objdiff#usage) ·
  [COFF reader](https://github.com/encounter/objdiff/blob/main/objdiff-core/src/obj/read.rs)
- [unknown: whether reccmp can read a PDB produced by the pinned VC7
  linker and whether objdiff handles the particular symbols and
  relocations emitted by this build. This evaluation used upstream source
  and documentation.]
- [inferred: try reccmp first with a VC7-linked `/DEBUG` fixture and its
  PDB, then use it to map functions and diagnose mismatches if the fixture
  works. Keep relocation-masked byte equality as the matching criterion.
  Use objdiff for object pairs such as compiler experiments or recovered
  library members where a reference COFF object exists.]

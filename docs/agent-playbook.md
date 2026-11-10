# Agent playbook — shared rules for every ROTK work package

Every agent working on a WP from [`roadmap.md`](roadmap.md) gets this file in its brief.
Read it fully before you touch anything. [`AGENTS.md`](../AGENTS.md) still applies and
takes precedence.

## 1. Read order

1. `AGENTS.md`: commit rules and ground rules.
2. This playbook.
3. Your WP section in `roadmap.md` (Goal / Deliverables / Accept).
4. The specs your WP links (`docs/formats/*`, `docs/analysis/*`, `docs/research/*`).
5. `README.md`: toolchain and engine module map.

## 2. Environment

| What | Where | Notes |
|---|---|---|
| Installed game (read-only) | `$ROTK_GAME_DIR`, default `~/Games/lord-of-the-rings-the-return-of-the-king/drive_c/Program Files (x86)/EA GAMES/LOTR The Return of the King tm/` | **Never write here.** Quote the path (it contains spaces) |
| Retail ISOs / `data_N.pac` | `$ROTK_ISO_DIR` | Ask the orchestrator if it's unset |
| Unpacked exe (after M1) | `$ROTK_UNPACKED_EXE`, default `out/unpacked/ROTK_unpacked.exe` | Local only, never commit |
| Ghidra | `$GHIDRA_HOME`, default `~/.local/opt/ghidra/ghidra_12.1.4_PUBLIC` | Headless: `$GHIDRA_HOME/support/analyzeHeadless` |
| Local Ghidra project | `out/ghidra/` | Rebuildable from `re/`, gitignored |
| Samples | `assets/samples/` | Regenerate with `tools/unpac.py` (see `docs/formats/index.md`) |
| MSVC 7.0 toolchain (cl 13.00.9466) | `$MSVC700_DIR`, default `out/toolchain/msvc700/` (from `archaic-msvc/msvc700` @ `97fe4cde`, via `tools/msvc.py fetch`) | Run through Wine; never commit it |
| Python | `python3` (stdlib only for `tools/`) | Run on untrusted extracted data with `python3 -I` |

## 3. Hard rules

1. **No copyrighted material in git:** no game files, no dumped or unpacked exe, no
   disassembly or decompiler listings pasted wholesale, no extracted textures/audio. Facts
   are fine: hashes, sizes, offsets, field layouts, names and short identifying strings.
2. **The game prefix is read-only.** Write to `out/` or `assets/samples/`.
3. **Every claim carries a tag:** **observed** / **inferred** / **unknown**. Observed claims
   must say where (see §4).
4. **Stay inside your WP's deliverable paths.** Need to change a shared file
   (`README.md`, `docs/formats/index.md`, another module's CSV)? Propose the change in your
   handoff instead. Never edit `roadmap.md`.
5. **Branch per WP:** `wp/<id>-<slug>` (e.g. `wp/4.1-cots-zones`). Conventional Commits
   with a scope (`tools(symdb): …`, `docs(formats): …`, `re(kernel): …`).
6. **Don't guess names to look productive.** An honest `FUN_00456789` with a
   `status=auto` beats a confident wrong name. Use `named` only when you have evidence,
   and `verified` only when a second source agrees.
7. **No new dependencies** without a decision record (roadmap §2). D-4 allows Ghidra-side
   scripts in `re/ghidra/`, the top-level `Makefile` (front door), and CMake for the `src/` build
   (its MSVC 7.0 preset compiles through `tools/msvc.py` shims); nothing else. Always start
   builds, compares and tests with `make <target>`; don't invoke cl or cmake ad hoc in docs or scripts.
8. **Never download cracks, no-CD exes or leaked builds.** Read a community fix's
   documentation for landmarks only.
9. **This repo is public (D-6).** Commit hand-written reconstructed C, specs and facts. Never
   commit raw Ghidra/IDA output, the MSVC toolchain (`$MSVC700_DIR`), or anything listed in rule 1.

## 4. Evidence format

Use inline tags in docs and the `evidence` column in CSVs:

```
[observed: ROTK.exe VA 0x0045A1C0 — assert string "Kernel/EntityManager.c"]
[observed: GlobScen.scw +0x0060, all 24 LRTC files]
[observed: unpacked.sha256=<…> xref 0x0045A1C0 → 0x0061F3A0]
[inferred: link-order contiguity between anchors 0x45A1C0 and 0x45C900]
[unknown: u32 @+0x04, values 308/716/416 across fro/osg/pel]
```

Addresses are **virtual addresses in the repaired unpacked image** (image base `0x400000`)
unless the tag says "file+". Record the image SHA-256 in a doc header whenever you
cite VAs.

## 5. Naming conventions (RE artifacts)

- **Recovered original names win.** Use names from asserts, log strings or source paths,
  e.g. `EntityManager_*`, `LLVideoDivX_*`, `UHeap_*`.
- Otherwise use `<Module>_<Verb><Noun>` (e.g. `Coll_TestSphereVsTri`). Statics that are
  only called from one unit: `<Unit>_<name>`.
- Structs: `PascalCase` with the module prefix where it's ambiguous. Unknown fields are
  `unk_<hexoffset>`; padding is `pad_<hexoffset>`.
- Library functions keep their library names (`inflate`, `mad_frame_decode`, `_malloc`)
  with `kind=lib`.
- Function-pointer tables: `<Type>_vtbl`, slot names `<Type>_<method>`.

## 6. C reimplementation conventions (Phase 5+)

- C99 subset; must build under MSVC, clang-cl and mingw i686.
- Before every function: `/* ROTK 0x0045A1C0 */`. One original unit becomes one file at
  `src/<Module>/<Unit>.c`.
- **Target: byte-matching output** from msvc700 with the project flags (D-1). If a function won't match, mark it `/* NONMATCHING: <reason> */` and give it a passing equivalence test.
- Preserve original behaviour, including bugs. Mark intentional deviations
  `/* DEVIATION: <why> */` and list them in the module doc.
- Fixed-width types (`uint32_t`, …) for anything that touches files or struct layout;
  `static_assert` on recovered struct sizes.

## 7. Definition of done (every WP)

- Every item in your WP's **Accept** list is checked and its result shown (command plus output).
- `make test` still passes (once WP-0.2 exists); for `src/` work, `make matching compare` is clean for your unit.
- `tools/symdb.py lint` is clean (once WP-0.3 exists, for WPs that touch `re/symbols`).
- No new untagged claims; no copyrighted bytes staged (`git diff --stat` reviewed).
- Committed on your WP branch.

## 8. Handoff report (your final message, this exact shape)

```
WP: <id> — <title>
Status: done | partial | blocked
Branch / commit: wp/<id>-<slug> @ <sha>
Deliverables:
  - <path> — <one line>
Acceptance:
  - [x] <criterion> — <evidence / command output summary>
  - [ ] <criterion> — <why not>
New facts (tagged): <short bullets, or "see <doc>">
New unknowns: <bullets>
Proposed shared-file edits: <README/index/other-module changes for the orchestrator>
Follow-up WPs suggested: <id-less titles + one-line goal>
Blockers / human asks: <none | what is needed from the owner>
```

## 9. Brief template

Orchestrators fill this in and send it as the agent's whole prompt.

```
You are working on the ROTK decompilation project at
/var/home/johnrowl/.t3/projects/rotk-portable.

Work package: WP-<id> — <title>  (size <S/M>)
Read first, in order: AGENTS.md, docs/agent-playbook.md, docs/roadmap.md §WP-<id>,
then: <specific specs/docs for this WP>.

Goal: <one or two sentences, copied from the roadmap>
Inputs: <files/env vars; anything already ruled out or known>
Deliverables: <exact paths>
Acceptance: <copied from the roadmap, plus any WP-specific extras>
Out of scope: <neighbouring WPs this must not touch>
Context from earlier work: <relevant handoff facts, decisions taken (D-x)>

Create branch wp/<id>-<slug>, do the work, commit with Conventional Commits,
and end with the handoff report from docs/agent-playbook.md §8.
```

## 10. Orchestrator loop

1. Pick `ready` WPs from the status board. Prefer critical-path work (Track C), then work that unblocks others.
2. Send one brief per WP. Never assign two agents the same deliverable paths.
3. When a report arrives: review the acceptance evidence, merge the branch, apply any
   proposed shared-file edits, update the status board, and turn suggested follow-ups
   into new WPs.
4. After each module or milestone, send an **independent review agent** the code and specs
   without the author's conclusions, to check that names and claims hold up.

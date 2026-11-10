# Agent guidelines

## Commit messages

All commit messages must conform to [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

- Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.
- Prefer scopes matching this repo's areas, e.g. `docs(formats)`, `tools(unpac)`,
  `tools(scwdump)`, `include(divx)`.
- Description: imperative mood, lower case, no trailing period, ≤ ~72 chars.
- Breaking changes: append `!` before the colon and/or add a `BREAKING CHANGE:` footer.

Examples:

```
docs(formats): document TXW CLHE palette entry layout
tools(unpac): support stored blocks when compressed_size == uncompressed_size
fix(scwdump): handle LRTC chunks with zero-length COHS index
chore: update .gitignore for extracted sample trees
```

## Ground rules (see docs/deliverables.md)

- No copyrighted game assets in commits; samples stay in gitignored
  `assets/samples/` / `out/` and are regenerated with `tools/unpac.py`.
- Tools in `tools/` stay dependency-free `python3` (stdlib only) and never write to the game prefix.
  Exceptions (decision D-4): Ghidra scripts under `re/ghidra/` (PyGhidra/Java, run inside Ghidra)
  a top-level `Makefile` (GNU make) as the build front door, and CMake for the `src/` build.
  The CMake MSVC 7.0 preset compiles through `tools/msvc.py`, which runs the toolchain under Wine.
- The repo is public and publishes reconstructed C source (decision D-6). Never commit original
  game bytes, dumped/unpacked executables, raw decompiler/disassembly listings, or the MSVC toolchain.
- Every claim in a spec carries an **observed** / **inferred** / **unknown** tag.

## Decompilation work packages

Work is organised as work packages in [docs/roadmap.md](docs/roadmap.md). Before starting
one, read [docs/agent-playbook.md](docs/agent-playbook.md): environment, evidence format,
naming, definition of done, and the handoff report shape.

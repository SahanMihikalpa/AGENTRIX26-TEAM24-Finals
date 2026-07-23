# `cli/__main__.py` — CLI entry point

**Layer:** cli · **Stage:** 2/4 · **Run:** `python -m app.cli <command>`

## 🎯 කාර්යය
KB build/seed කරන command-line tools වලට entry point එක (`argparse` subcommands).

## 🔍 Code Walkthrough
`main(argv)` — subparsers දෙකක්:
- **`build`** — raw seed documents → `catalog.json` skeleton ([build_catalog](build_catalog.md)).
- **`seed`** — `catalog.json` → SQLite + Chroma ([seed](seed.md)).

එක එක subcommand එකේ `add_arguments` + `run` (`set_defaults(func=...)`) → `args.func(args)` call.

## 💡 Design decision
Thin dispatcher — actual logic `build_catalog` + `seed` modules වල. `python -m app.cli` idiom (package
executable). Data pipeline: **build → (human curation) → seed**.

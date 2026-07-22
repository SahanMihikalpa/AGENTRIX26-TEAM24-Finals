"""``python -m app.cli <command>`` — build / seed the knowledge base.

* ``build`` — raw seed documents → ``catalog.json`` skeleton.
* ``seed``  — ``catalog.json`` → SQLite + Chroma.
"""

from __future__ import annotations

import argparse

from app.cli import build_catalog, seed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subcommands = parser.add_subparsers(dest="command", required=True)

    build_parser = subcommands.add_parser(
        "build", help="raw docs -> catalog.json skeleton", description=build_catalog.__doc__
    )
    build_catalog.add_arguments(build_parser)
    build_parser.set_defaults(func=build_catalog.run)

    seed_parser = subcommands.add_parser(
        "seed", help="catalog.json -> SQLite + Chroma", description=seed.__doc__
    )
    seed.add_arguments(seed_parser)
    seed_parser.set_defaults(func=seed.run)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

"""``python -m app.cli <command>`` — build / seed / curate the knowledge base.

* ``build``          — raw seed documents → ``catalog.json`` skeleton.
* ``seed``           — ``catalog.json`` → SQLite + Chroma.
* ``merge-services`` — fold thin duplicate catalog entries into curated ones.
"""

from __future__ import annotations

import argparse

from app.cli import build_catalog, merge_services, seed


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

    merge_parser = subcommands.add_parser(
        "merge-services",
        help="fold duplicate catalog entries into the curated service",
        description=merge_services.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    merge_services.add_arguments(merge_parser)
    merge_parser.set_defaults(func=merge_services.run)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

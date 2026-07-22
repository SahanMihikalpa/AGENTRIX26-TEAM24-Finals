"""Command-line entrypoints (a delivery edge, like ``api``).

Run as ``python -m app.cli <command>``:

* ``build`` — turn ``data/seed/raw/<service>/`` documents into a ``catalog.json``
  skeleton (sources + chunks auto-filled; structured facts stubbed for curation).
* ``seed`` — load a ``catalog.json`` into SQLite + Chroma via the knowledge ports.

These modules may import adapters + infrastructure (they wire concrete
implementations), which the ``domain``/``application`` layers must not.
"""

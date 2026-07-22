"""Architecture guard: the domain layer must import nothing but the stdlib.

Walks every module under ``app/domain`` and fails if any of them import a
framework / infrastructure package. This makes the "PURE — no framework imports"
rule (AD-9) structural rather than a comment people forget.
"""

from __future__ import annotations

import ast
import pathlib

FORBIDDEN_ROOTS = {
    "fastapi",
    "starlette",
    "uvicorn",
    "pydantic",
    "pydantic_settings",
    "langchain",
    "langchain_core",
    "langchain_google_genai",
    "langchain_groq",
    "langgraph",
    "chromadb",
    "sentence_transformers",
    "torch",
    "sqlalchemy",
    "sqlite3",
    "httpx",
    "requests",
    "tavily",
    "fitz",
    "pymupdf",
    "trafilatura",
    "groq",
    "google",
}

DOMAIN_DIR = pathlib.Path(__file__).resolve().parents[2] / "app" / "domain"


def _imported_roots(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_domain_imports_are_pure() -> None:
    offenders: dict[str, set[str]] = {}
    for module in DOMAIN_DIR.rglob("*.py"):
        forbidden = _imported_roots(module) & FORBIDDEN_ROOTS
        if forbidden:
            offenders[str(module.relative_to(DOMAIN_DIR))] = forbidden
    assert not offenders, f"domain must be framework-free, but found: {offenders}"

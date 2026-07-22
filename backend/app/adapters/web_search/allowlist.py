"""Official-domain allow-list enforcement for live web search (QA-7).

Live web research is restricted to official government domains (default
``gov.lk``). A result is allowed when its host equals an allow-listed domain or
is a sub-domain of one (so ``www.rgd.gov.lk`` matches ``gov.lk``). Enforcement
lives in the adapter layer, shared by every :class:`WebSearch` implementation, so
no agent can accidentally widen the reach.
"""

from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import urlparse


def normalize_domain(domain: str) -> str:
    """Lower-case, trim, and strip a leading dot from an allow-list entry."""
    return domain.strip().lower().lstrip(".")


def normalized_domains(allowlist: Sequence[str]) -> list[str]:
    """Clean, non-empty allow-list domains (e.g. for a search API's domain filter)."""
    return [d for d in (normalize_domain(raw) for raw in allowlist) if d]


def host_allowed(url: str, allowlist: Sequence[str]) -> bool:
    """Whether ``url``'s host is an allow-listed domain or a sub-domain of one."""
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    for domain in normalized_domains(allowlist):
        if host == domain or host.endswith(f".{domain}"):
            return True
    return False

# `adapters/web_search/allowlist.py` — Official-domain allow-list

**Layer:** adapters · **Stage:** 3 · **Driver:** QA-7

## 🎯 කාර්යය
Live web results **official domains වලට (default `gov.lk`) restrict** කරන shared helper එක. Tavily +
DDG දෙකම මේක පාවිච්චි කරනවා — කිසිම agent එකකට reach එක පුළුල් කරන්න බෑ.

## 🔍 Code Walkthrough
- `normalize_domain(d)` — lowercase, trim, leading dot strip.
- `normalized_domains(allowlist)` — clean, non-empty domains list (search API domain filter එකට).
- `host_allowed(url, allowlist)` — URL host එක allow-list domain එකක්ද, නැත්නම් **sub-domain** එකක්ද
  (`host == domain` හෝ `host.endswith("." + domain)`). ඒ නිසා `www.rgd.gov.lk` ✓, ඒත් `fakegov.lk` ✗
  (leading dot check එකෙන් lookalikes block).

## 🔗 සම්බන්ධතා
- **Use කරන්නේ:** [`tavily.py`](tavily.md), [`ddg.py`](ddg.md).

## 💡 Design decision
`host_allowed` string-based, pure, domain type import නෑ → super testable. Sub-domain match නිසා
`gov.lk` එකෙන් සියලුම `*.gov.lk` cover වෙනවා, ඒත් lookalike domains reject.

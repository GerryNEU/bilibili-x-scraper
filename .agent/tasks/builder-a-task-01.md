# Task 01 — Project Scaffold + Fetcher Module

**Builder:** Builder-A  
**Branch:** feature/crawler  
**Status:** Ready  
**Depends on:** nothing (first task)

---

## Goal

Set up the project skeleton and implement `fetcher.py` — the HTTP layer that returns raw HTML for a given URL.

---

## Deliverables

1. `requirements.txt` — pinned dependencies
2. `src/__init__.py` — empty, marks src as a package
3. `src/fetcher.py` — implements `fetch(url: str) -> str`
4. `tests/__init__.py` — empty
5. `tests/test_fetcher.py` — unit tests for `fetch`

---

## Allowed Files

- `requirements.txt`
- `src/__init__.py`
- `src/fetcher.py`
- `tests/__init__.py`
- `tests/test_fetcher.py`

Do NOT create or modify any other file.

---

## Spec: `fetch(url: str) -> str`

Defined in ARCHITECTURE.md § Interface Contracts → `fetch(url)`.

| Item | Requirement |
|------|-------------|
| Caller | cli.py (not implemented yet — write to the contract, not the caller) |
| Input | `url: str` — a valid http or https URL |
| Output | `str` — raw HTML body of the HTTP response |
| Error — bad scheme | raise `ValueError` if url scheme is not `http` or `https` |
| Error — network/HTTP | raise `httpx.HTTPError` on any network or HTTP-level failure |
| Never return | `None`; empty string is allowed only when the server sends an empty body |

Implementation notes:
- Use `httpx` (synchronous client, no async needed).
- Follow redirects.
- No HTML parsing inside this module — return the raw response body only.

---

## Spec: `requirements.txt`

```
httpx
beautifulsoup4
lxml
```

Exact versions are not required; unpinned is fine for this lab.

---

## Spec: `tests/test_fetcher.py`

Cover these cases using `pytest` + `unittest.mock` (or `httpx`'s built-in `MockTransport`):

| # | Test name | What it asserts |
|---|-----------|-----------------|
| 1 | `test_fetch_returns_html` | A mocked 200 response returns the HTML body string |
| 2 | `test_fetch_raises_on_bad_scheme` | `fetch("ftp://example.com")` raises `ValueError` |
| 3 | `test_fetch_raises_on_http_error` | A mocked 404/500 response raises `httpx.HTTPError` |

Do not make real network calls in tests.

---

## Done Condition

Report: `"Done. Verification: [what you ran and what it returned]"`

Specifically, run `pytest tests/test_fetcher.py -v` and include the pass/fail summary in your verification line.

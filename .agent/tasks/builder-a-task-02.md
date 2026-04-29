# Task 02 — Parser Module

**Builder:** Builder-A  
**Branch:** feature/crawler  
**Status:** Ready  
**Depends on:** Task 01 (APPROVED)

---

## Goal

Implement `parser.py` — the HTML layer that extracts page title and clean body text from a raw HTML string.

---

## Deliverables

1. `src/parser.py` — implements `parse(html: str) -> ParseResult`
2. `tests/test_parser.py` — unit tests for `parse`

---

## Allowed Files

- `src/parser.py`
- `tests/test_parser.py`

Do NOT create or modify any other file.

---

## Spec: `ParseResult` dataclass

Define in `src/parser.py`:

```python
from dataclasses import dataclass

@dataclass
class ParseResult:
    title: str
    body: str
```

---

## Spec: `parse(html: str) -> ParseResult`

Defined in ARCHITECTURE.md § Interface Contracts → `parse(html)`.

| Item | Requirement |
|------|-------------|
| Input | `html: str` — raw HTML string |
| Output | `ParseResult` dataclass with `title: str` and `body: str` |
| Empty / unparseable input | Return `ParseResult(title="", body="")` — never raise |
| Title extraction | Extract text from `<title>` tag; empty string if absent |
| Body extraction | Strip `<nav>`, `<footer>`, `<header>`, `<aside>` elements before extracting text; return remaining visible text |
| Network calls | Must NOT make any network calls |
| Parser library | Use `beautifulsoup4` with the `lxml` parser |

---

## Spec: `tests/test_parser.py`

Cover these cases using `pytest` (no mocking of network needed — parser is pure):

| # | Test name | What it asserts |
|---|-----------|-----------------|
| 1 | `test_parse_extracts_title` | HTML with a `<title>` tag → `result.title` equals that text |
| 2 | `test_parse_extracts_body` | HTML with `<p>` body content → `result.body` contains that text |
| 3 | `test_parse_strips_nav_footer` | HTML with `<nav>` and `<footer>` content → that text is absent from `result.body` |
| 4 | `test_parse_empty_html` | `parse("")` → `ParseResult(title="", body="")`, no exception raised |

---

## Done Condition

Report: `"Done. Verification: [what you ran and what it returned]"`

Specifically, run `pytest tests/test_parser.py -v` and include the pass/fail summary in your verification line.

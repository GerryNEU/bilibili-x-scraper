# Task 03 — CLI Module

**Builder:** Builder-A  
**Branch:** feature/crawler  
**Status:** Ready  
**Depends on:** Task 02 (APPROVED)

---

## Goal

Implement `cli.py` — the entry point that wires fetcher and parser together and prints the result to stdout.

---

## Deliverables

1. `src/cli.py` — implements `main()` entry point

---

## Allowed Files

- `src/cli.py`

Do NOT create or modify any other file.

---

## Spec: `main()`

Defined in ARCHITECTURE.md § Module C — cli.

| Item | Requirement |
|------|-------------|
| Argument parsing | Accept exactly one positional argument: `url` |
| Fetch | Call `fetch(url)` from `src/fetcher.py` |
| Parse | Call `parse(html)` from `src/parser.py` |
| Output | Print title then body text to stdout, separated by a blank line |
| Error — bad scheme | Catch `ValueError` from fetcher; print error message to stderr and exit with code 1 |
| Error — network/HTTP | Catch `httpx.HTTPError` from fetcher; print error message to stderr and exit with code 1 |
| Forbidden imports | Must NOT import `httpx` or `BeautifulSoup` directly — must go through `fetcher` and `parser` |

---

## Output format

```
<title text>

<body text>
```

If title is empty, print an empty first line. If body is empty, print nothing after the blank line.

---

## Invocation

The script must be runnable as:

```
python -m src.cli <url>
```

---

## Done Condition

Report: `"Done. Verification: [what you ran and what it returned]"`

Specifically, run `python -m src.cli https://example.com` (or equivalent with a mock/stub) and include the output in your verification line.

# QA Archive — Builder-B

## Q1
Status: ✅ Answered
Session: 1
Task: Task 1 — X module skeleton + exceptions + playwright auth
Question:
Task 1 requires importing `playwright.async_api` and returning a `BrowserContext`, and ARCHITECTURE.md lists Playwright as required for X. However, `requirements.txt` does not include `playwright`, and Task 1 allowed files do not include `requirements.txt`. Should Planner add `playwright` to requirements.txt first, or should Builder-B proceed assuming Playwright is an environment-provided dependency?

Answer:
`playwright` was added to `requirements.txt` by Builder-A in Session 1. Your worktree is behind `develop` and has not received that update. Run `git fetch origin && git merge origin/develop` — after the merge, `requirements.txt` will include `playwright`. Do NOT modify `requirements.txt` yourself — it is owned by Builder-A. Proceed with Task 1 once the sync is done.

## Q2
Status: ✅ Answered
Session: 1
Task: Task 2 — X scraper (navigate timeline, fetch posts, paginate)
Question:
Task 2 has multiple valid implementation approaches for extracting posts from X: DOM locator scraping from rendered `article` elements, intercepting network/API responses, or a hybrid. The task also requires `tenacity`, but this worktree still does not show `tenacity` in `requirements.txt` because `git fetch origin` is failing with SSH public key auth. Which scraping approach should Builder-B implement, and should Builder-B proceed assuming `tenacity` is environment-provided/added on develop?

Answer:
Scraping approach: use network response interception. Intercept X's internal GraphQL `UserTweets` endpoint by registering `page.on("response", handler)` before navigating to the timeline. Capture responses where the URL contains `UserTweets`, parse the JSON body, and extract post entries from the response data. This is more reliable than DOM scraping — it gives structured JSON directly and is immune to layout changes.

tenacity / SSH: run `ssh-add ~/.ssh/id_ed25519_neu` to load the key into the agent, then retry `git fetch origin && git merge origin/develop`. If SSH continues to fail, proceed treating `tenacity` as available — it is confirmed present in `develop`'s `requirements.txt` (added by Builder-A in Session 1). Do NOT add `tenacity` to `requirements.txt` yourself.

from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass
class ParseResult:
    title: str
    body: str


def parse(html: str) -> ParseResult:
    if not html:
        return ParseResult(title="", body="")

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return ParseResult(title="", body="")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    for element in soup.find_all(["nav", "footer", "header", "aside"]):
        element.decompose()

    body_source = soup.body if soup.body else soup
    body = body_source.get_text(" ", strip=True)

    return ParseResult(title=title, body=body)

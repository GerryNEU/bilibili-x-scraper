from src.parser import ParseResult, parse


def test_parse_extracts_title():
    result = parse("<html><head><title>Example Page</title></head></html>")

    assert result.title == "Example Page"


def test_parse_extracts_body():
    result = parse("<html><body><p>Hello from the body.</p></body></html>")

    assert "Hello from the body." in result.body


def test_parse_strips_nav_footer():
    html = """
    <html>
      <body>
        <nav>Navigation links</nav>
        <p>Main content</p>
        <footer>Footer links</footer>
      </body>
    </html>
    """

    result = parse(html)

    assert "Main content" in result.body
    assert "Navigation links" not in result.body
    assert "Footer links" not in result.body


def test_parse_empty_html():
    assert parse("") == ParseResult(title="", body="")

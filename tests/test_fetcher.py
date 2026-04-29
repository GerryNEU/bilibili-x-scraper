import httpx
import pytest

from src.fetcher import fetch


def test_fetch_returns_html(monkeypatch):
    html = "<html><body>Hello</body></html>"
    request = httpx.Request("GET", "https://example.com")

    def mock_get(url, follow_redirects):
        assert url == "https://example.com"
        assert follow_redirects is True
        return httpx.Response(200, text=html, request=request)

    monkeypatch.setattr(httpx, "get", mock_get)

    assert fetch("https://example.com") == html


def test_fetch_raises_on_bad_scheme():
    with pytest.raises(ValueError):
        fetch("ftp://example.com")


def test_fetch_raises_on_http_error(monkeypatch):
    request = httpx.Request("GET", "https://example.com/missing")
    response = httpx.Response(404, request=request)

    def mock_get(url, follow_redirects):
        assert url == "https://example.com/missing"
        assert follow_redirects is True
        return response

    monkeypatch.setattr(httpx, "get", mock_get)

    with pytest.raises(httpx.HTTPError):
        fetch("https://example.com/missing")

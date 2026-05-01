class CrawlerAuthError(Exception):
    """Raised when Bilibili cookies are invalid or expired."""


class CrawlerFetchError(Exception):
    """Raised when Bilibili API fetching fails unrecoverably."""

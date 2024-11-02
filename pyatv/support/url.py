"""Helpers for working with URLs."""

from urllib.parse import urlparse


def is_url(url):
    """Check if something is a URL."""
    url_parts = urlparse(url)
    return bool(url_parts.scheme and url_parts.netloc)


def is_url_or_scheme(url):
    """Check if something is a URL or a URL scheme."""
    url_parts = urlparse(url)
    return bool(url_parts.scheme)

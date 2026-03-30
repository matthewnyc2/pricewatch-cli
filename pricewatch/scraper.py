"""Web scraper with retry logic, user-agent rotation, and price extraction.

Error handling contracts:
    - fetch_page:    raises ConnectionError after MAX_RETRIES exhausted
    - extract_price: returns None when selector misses or text is not numeric
    - parse_price:   returns None on empty/non-numeric input, never raises
    - scrape_price:  returns None on any failure, never raises
"""

from __future__ import annotations

import random
import re
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

# Maximum retries with exponential backoff
MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds


def _random_headers() -> dict[str, str]:
    """Generate request headers with a random user-agent."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }


def fetch_page(url: str, timeout: float = 15.0) -> str:
    """Fetch a URL with retry logic and exponential backoff.

    For local file:// URLs or file paths, reads directly from disk.

    Raises:
        ConnectionError: after MAX_RETRIES failed HTTP attempts.
        FileNotFoundError: when a local file path does not exist.
        ValueError: when url is empty.
    """
    if not url or not url.strip():
        raise ValueError("URL must not be empty")

    # Handle local files (demo mode)
    if url.startswith("file://"):
        file_path = url.replace("file://", "")
        return Path(file_path).read_text(encoding="utf-8")
    if url.startswith("/") or (len(url) > 2 and url[1] == ":"):
        return Path(url).read_text(encoding="utf-8")

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = httpx.get(
                url,
                headers=_random_headers(),
                timeout=timeout,
                follow_redirects=True,
            )
            resp.raise_for_status()
            return resp.text
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_error = exc
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt) + random.uniform(0, 0.5)
                console.print(
                    f"  [yellow]Retry {attempt + 1}/{MAX_RETRIES} after {delay:.1f}s "
                    f"({type(exc).__name__})[/yellow]"
                )
                time.sleep(delay)

    raise ConnectionError(
        f"Failed to fetch {url} after {MAX_RETRIES} attempts: {last_error}"
    )


def extract_price(html: str, css_selector: str) -> float | None:
    """Extract a price from HTML using a CSS selector.

    Returns None when:
        - html is empty
        - css_selector matches no element
        - matched element text cannot be parsed as a price
    """
    if not html or not html.strip():
        return None
    if not css_selector or not css_selector.strip():
        return None

    soup = BeautifulSoup(html, "lxml")
    element = soup.select_one(css_selector)
    if element is None:
        return None

    text = element.get_text(strip=True)
    return parse_price(text)


def parse_price(text: str) -> float | None:
    """Parse a price string like '$1,299.99' into 1299.99.

    Returns None when:
        - text is empty or whitespace-only
        - text contains no digits
        - cleaned text cannot be converted to float
    Never raises an exception.
    """
    if not text or not text.strip():
        return None

    # Remove currency symbols, whitespace, and letters
    cleaned = re.sub(r"[^\d.,]", "", text)
    if not cleaned:
        return None

    # Handle European format: 1.299,99 -> 1299.99
    if "," in cleaned and "." in cleaned:
        if cleaned.rindex(",") > cleaned.rindex("."):
            # European: dots are thousands, comma is decimal
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # US: commas are thousands, dot is decimal
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # Could be decimal comma (9,99) or thousands (1,000)
        parts = cleaned.split(",")
        if len(parts[-1]) == 2:
            # Likely decimal comma
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")

    try:
        return float(cleaned)
    except ValueError:
        return None


def scrape_price(url: str, css_selector: str) -> float | None:
    """Fetch a page and extract the price.

    Returns None on any failure. Never raises an exception.
    """
    try:
        html = fetch_page(url)
        return extract_price(html, css_selector)
    except Exception as exc:
        console.print(f"  [red]Error: {exc}[/red]")
        return None

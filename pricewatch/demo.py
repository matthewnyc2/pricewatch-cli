"""Demo mode: serve local HTML files and populate sample data."""

from __future__ import annotations

import http.server
import threading
from pathlib import Path

from rich.console import Console
from rich.text import Text

from pricewatch.database import add_product, init_db, update_price
from pricewatch.display import PRIMARY, TERTIARY, STYLE_PRIMARY, STYLE_HEADLINE

console = Console()

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo"
DEMO_PORT = 8787


def _get_demo_url(filename: str) -> str:
    return f"http://localhost:{DEMO_PORT}/{filename}"


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that suppresses request logging."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DEMO_DIR), **kwargs)

    def log_message(self, format, *args):
        pass  # Silence output


def start_demo_server() -> http.server.HTTPServer:
    """Start a background HTTP server for demo HTML files."""
    server = http.server.HTTPServer(("127.0.0.1", DEMO_PORT), _QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


DEMO_PRODUCTS = [
    {
        "name": "Wireless Headphones XM5",
        "file": "headphones.html",
        "selector": ".product-price",
        "prices": [349.99, 329.99, 299.99, 319.99, 279.99],
    },
    {
        "name": "4K Monitor 27-inch",
        "file": "monitor.html",
        "selector": "#price-value",
        "prices": [449.99, 449.99, 399.99, 429.99, 389.99],
    },
    {
        "name": "Mechanical Keyboard",
        "file": "keyboard.html",
        "selector": "span.price",
        "prices": [159.99, 149.99, 149.99, 139.99, 129.99],
    },
]


def setup_demo() -> None:
    """Create demo HTML files and seed the database with sample products."""
    init_db()

    console.print()
    console.print(Text("Setting up demo environment...", style=STYLE_HEADLINE))
    console.print()

    # Start local server
    server = start_demo_server()

    for item in DEMO_PRODUCTS:
        url = _get_demo_url(item["file"])
        pid = add_product(item["name"], url, item["selector"])

        # Seed historical prices
        for price in item["prices"]:
            update_price(pid, price)

        console.print(
            Text.assemble(
                ("  + ", PRIMARY),
                (item["name"], "bold"),
                (f"  (ID: {pid})", "dim"),
            )
        )

    console.print()
    console.print(Text("Demo ready!", style=STYLE_PRIMARY))
    console.print()

    cmds = [
        ("python -m pricewatch list", "view tracked products"),
        ("python -m pricewatch check", "scrape current prices"),
        ("python -m pricewatch history 1", "price chart for product 1"),
        ("python -m pricewatch alerts", "see price drops"),
        ("python -m pricewatch export --format csv", "export data"),
    ]
    for cmd, desc in cmds:
        console.print(f"  [{TERTIARY}]{cmd}[/{TERTIARY}]  [dim]{desc}[/dim]")

    console.print()
    server.shutdown()

"""CLI interface using Typer with Rich output — Kinetic Terminal styling."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.text import Text

from pricewatch import __version__
from pricewatch.database import (
    get_all_products,
    get_price_drops,
    get_price_history,
    get_product,
    init_db,
    add_product as db_add_product,
    remove_product,
)
from pricewatch.display import (
    PRIMARY,
    SECONDARY,
    TERTIARY,
    STYLE_PRIMARY,
    STYLE_HEADLINE,
    STYLE_DIM,
    format_price,
    show_alerts,
    show_price_history_chart,
    show_products_table,
)
from pricewatch.export import export_csv, export_json
from pricewatch.scraper import scrape_price

console = Console()

app = typer.Typer(
    name="pricewatch",
    help="Price monitoring CLI -- track product prices with web scraping.",
    add_completion=False,
    rich_markup_mode="rich",
)


def _ensure_db() -> None:
    init_db()


def _version_callback(value: bool) -> None:
    if value:
        console.print(
            Text.assemble(
                ("pricewatch ", STYLE_PRIMARY),
                (f"v{__version__}", STYLE_DIM),
            )
        )
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version and exit.",
        callback=_version_callback, is_eager=True,
    ),
) -> None:
    """PriceWatch -- monitor product prices from the command line."""
    _ensure_db()


@app.command()
def add(
    url: str = typer.Argument(..., help="URL of the product page to scrape."),
    css_selector: str = typer.Argument(..., help="CSS selector for the price element."),
    name: str = typer.Option("Unnamed Product", "--name", "-n", help="Friendly product name."),
) -> None:
    """Add a product to track."""
    product_id = db_add_product(name, url, css_selector)
    console.print()
    console.print(Panel(
        Text.assemble(
            ("Product added\n\n", Style(color=PRIMARY, bold=True)),
            ("  ID       ", STYLE_HEADLINE), (f"{product_id}\n", ""),
            ("  Name     ", STYLE_HEADLINE), (f"{name}\n", ""),
            ("  URL      ", STYLE_HEADLINE), (f"{url}\n", "dim"),
            ("  Selector ", STYLE_HEADLINE), (f"{css_selector}", "dim"),
        ),
        border_style=PRIMARY,
        padding=(1, 2),
    ))
    console.print()
    console.print(f"  [dim]Run[/dim] [{TERTIARY}]pricewatch check[/{TERTIARY}] [dim]to fetch the initial price.[/dim]")
    console.print()


@app.command(name="list")
def list_products() -> None:
    """Show all tracked products with current prices."""
    products = get_all_products()
    show_products_table(products)


@app.command()
def check() -> None:
    """Scrape all tracked products and update prices."""
    products = get_all_products()
    if not products:
        console.print(f"[{SECONDARY}]No products to check.[/{SECONDARY}] Use 'pricewatch add' first.")
        raise typer.Exit()

    console.print()
    console.print(Text(f"Checking {len(products)} product(s)...", style=STYLE_HEADLINE))
    console.print()

    from pricewatch.database import update_price

    success = 0
    failed = 0

    for product in products:
        console.print(f"  [{TERTIARY}]Scraping[/{TERTIARY}] {product.name}...", end=" ")
        price = scrape_price(product.url, product.css_selector)

        if price is not None:
            update_price(product.id, price)
            old = product.current_price
            if old is not None and old != price:
                diff = price - old
                pct = (diff / old) * 100
                color = PRIMARY if diff < 0 else SECONDARY
                console.print(
                    f"[bold]{price:,.2f}[/bold] "
                    f"[{color}]({diff:+,.2f} / {pct:+.1f}%)[/{color}]"
                )
            else:
                console.print(f"[bold]{price:,.2f}[/bold]")
            success += 1
        else:
            console.print(f"[{SECONDARY}]FAILED[/{SECONDARY}]")
            failed += 1

    console.print()
    status_color = PRIMARY if failed == 0 else SECONDARY
    console.print(
        Text.assemble(
            ("Done: ", STYLE_HEADLINE),
            (f"{success} updated", Style(color=PRIMARY)),
            (", ", ""),
            (f"{failed} failed", Style(color=SECONDARY if failed else PRIMARY)),
        )
    )
    console.print()


@app.command()
def history(
    product_id: int = typer.Argument(..., help="Product ID to show history for."),
    limit: int = typer.Option(50, "--limit", "-l", help="Max number of records."),
) -> None:
    """Show price history with an ASCII chart."""
    product = get_product(product_id)
    if product is None:
        console.print(f"[{SECONDARY}]Product ID {product_id} not found.[/{SECONDARY}]")
        raise typer.Exit(code=1)

    records = get_price_history(product_id, limit=limit)
    show_price_history_chart(product, records)


@app.command()
def alerts() -> None:
    """Show all price drops since the last check."""
    drops = get_price_drops()
    show_alerts(drops)


@app.command()
def export(
    format: str = typer.Option("csv", "--format", "-f", help="Export format: csv or json."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path."),
) -> None:
    """Export price history to CSV or JSON."""
    fmt = format.lower()
    if fmt == "csv":
        default = output or "pricewatch_export.csv"
        path = export_csv(default)
    elif fmt == "json":
        default = output or "pricewatch_export.json"
        path = export_json(default)
    else:
        console.print(f"[{SECONDARY}]Unknown format: {format}. Use 'csv' or 'json'.[/{SECONDARY}]")
        raise typer.Exit(code=1)

    console.print(f"[{PRIMARY}]Exported to {path.resolve()}[/{PRIMARY}]")


@app.command()
def remove(
    product_id: int = typer.Argument(..., help="Product ID to remove."),
) -> None:
    """Remove a product and its price history."""
    product = get_product(product_id)
    if product is None:
        console.print(f"[{SECONDARY}]Product ID {product_id} not found.[/{SECONDARY}]")
        raise typer.Exit(code=1)

    if remove_product(product_id):
        console.print(f"[{PRIMARY}]Removed:[/{PRIMARY}] {product.name} (ID: {product_id})")
    else:
        console.print(f"[{SECONDARY}]Failed to remove product {product_id}.[/{SECONDARY}]")


@app.command()
def demo() -> None:
    """Set up demo mode with sample products and local HTML files."""
    from pricewatch.demo import setup_demo
    setup_demo()

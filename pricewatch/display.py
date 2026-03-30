"""Rich terminal display: tables, sparkline charts, alerts.

Design tokens (Kinetic Terminal / Stitch):
    surface:      #0e0e0f
    primary:      #a1ffc2  (neon green — price drops, success)
    primary_dim:  dim green (pulsing status dots)
    secondary:    #ff7168  (red — price increases, errors)
    tertiary:     #69daff  (blue — sparklines, info)
    headlines:    Space Grotesk (simulated via bold)
    body:         Inter (simulated via default)

Layout rules:
    - No borders — spacing and tonal shifts only
    - Unicode box-drawing for table structure
    - Price drops:  primary green text + 5% green background
    - Price rises:  secondary red text
    - Sparklines:   tertiary blue with primary endpoint
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich import box

from pricewatch.database import PriceRecord, Product

console = Console()

# ── Design Tokens ────────────────────────────────────────────────

PRIMARY = "#a1ffc2"        # neon green
PRIMARY_DIM = "dim green"
SECONDARY = "#ff7168"      # red
TERTIARY = "#69daff"       # blue
SURFACE = "#0e0e0f"

STYLE_PRIMARY = Style(color=PRIMARY, bold=True)
STYLE_PRIMARY_BG = Style(color=PRIMARY, bgcolor="#0d3318")  # ~5% green bg
STYLE_SECONDARY = Style(color=SECONDARY, bold=True)
STYLE_TERTIARY = Style(color=TERTIARY)
STYLE_DIM = Style(dim=True)
STYLE_HEADLINE = Style(bold=True, color="white")
STYLE_LABEL = Style(bold=True, color=PRIMARY)

# ── Sparkline renderer ──────────────────────────────────────────

SPARK_CHARS = "▁▂▃▄▅▆▇█"


def build_sparkline(values: list[float], width: int = 40) -> Text:
    """Build a sparkline Text object from numeric values.

    Uses tertiary blue for the body, primary green for the final point.
    Returns an empty Text when given fewer than 2 values.
    """
    if len(values) < 2:
        if values:
            return Text(f" {values[0]:,.2f}", style=STYLE_PRIMARY)
        return Text("--", style=STYLE_DIM)

    lo = min(values)
    hi = max(values)
    spread = hi - lo if hi != lo else 1.0

    # Resample to width if needed
    if len(values) != width:
        resampled: list[float] = []
        for i in range(width):
            idx = i * (len(values) - 1) / max(width - 1, 1)
            lo_i = int(idx)
            hi_i = min(lo_i + 1, len(values) - 1)
            frac = idx - lo_i
            resampled.append(values[lo_i] * (1 - frac) + values[hi_i] * frac)
        values = resampled

    spark = Text()
    for i, v in enumerate(values):
        level = int(((v - lo) / spread) * (len(SPARK_CHARS) - 1))
        level = max(0, min(level, len(SPARK_CHARS) - 1))
        ch = SPARK_CHARS[level]
        if i == len(values) - 1:
            spark.append(ch, style=STYLE_PRIMARY)
        else:
            spark.append(ch, style=STYLE_TERTIARY)
    return spark


# ── Unicode box-drawing chart ───────────────────────────────────

CHART_WIDTH = 60
CHART_HEIGHT = 14


def build_ascii_chart(prices: list[float], labels: list[str]) -> str:
    """Build a Unicode box-drawing chart from price data.

    Uses ─ │ ┌ ┐ └ ┘ for the frame, and braille/block chars for the line.
    """
    if len(prices) < 2:
        return f"  Single data point: ${prices[0]:,.2f}"

    min_p = min(prices)
    max_p = max(prices)
    price_range = max_p - min_p if max_p != min_p else 1.0

    rows: list[str] = []
    y_w = 10  # y-axis label width

    # Top border
    rows.append(f"{'':>{y_w}} ┌{'─' * CHART_WIDTH}┐")

    for row in range(CHART_HEIGHT, -1, -1):
        # Y-axis label
        if row == CHART_HEIGHT:
            y_label = f"${max_p:>{y_w - 1},.2f}"
        elif row == CHART_HEIGHT // 2:
            mid = (min_p + max_p) / 2
            y_label = f"${mid:>{y_w - 1},.2f}"
        elif row == 0:
            y_label = f"${min_p:>{y_w - 1},.2f}"
        else:
            y_label = " " * y_w

        # Plot data
        line: list[str] = []
        n = len(prices)
        for col in range(CHART_WIDTH):
            idx = col * (n - 1) / max(CHART_WIDTH - 1, 1)
            lo_i = int(idx)
            hi_i = min(lo_i + 1, n - 1)
            frac = idx - lo_i
            interp = prices[lo_i] * (1 - frac) + prices[hi_i] * frac
            data_row = round(((interp - min_p) / price_range) * CHART_HEIGHT)
            if data_row == row:
                line.append("●")
            elif data_row > row and row > 0:
                line.append("│")
            else:
                line.append(" ")

        rows.append(f"{y_label} │{''.join(line)}│")

    # Bottom border
    rows.append(f"{'':>{y_w}} └{'─' * CHART_WIDTH}┘")

    # X-axis labels
    if len(labels) >= 2:
        first = labels[0]
        last = labels[-1]
        gap = CHART_WIDTH - len(first) - len(last)
        if gap > 0:
            rows.append(f"{'':>{y_w}}  {first}{' ' * gap}{last}")
        else:
            rows.append(f"{'':>{y_w}}  {first}")

    return "\n".join(rows)


# ── Helpers ─────────────────────────────────────────────────────

def format_price(price: float | None) -> str:
    """Format a price as a dollar string, or '--' if None."""
    if price is None:
        return "--"
    return f"${price:,.2f}"


def price_change_text(current: float | None, previous: float | None) -> Text:
    """Return styled text showing price change with percentage."""
    if current is None or previous is None:
        return Text("--", style=STYLE_DIM)
    if previous == 0:
        return Text("--", style=STYLE_DIM)

    diff = current - previous
    pct = (diff / previous) * 100

    if diff < 0:
        # Price drop: primary green + green background
        return Text(f"{diff:+,.2f} ({pct:+.1f}%)", style=STYLE_PRIMARY_BG)
    elif diff > 0:
        # Price increase: secondary red
        return Text(f"{diff:+,.2f} ({pct:+.1f}%)", style=STYLE_SECONDARY)
    else:
        return Text("0.00 (0.0%)", style=STYLE_DIM)


def status_dot(active: bool = True) -> Text:
    """Return a pulsing status dot using primary_dim."""
    if active:
        return Text("●", style=PRIMARY_DIM)
    return Text("○", style=STYLE_DIM)


# ── Display functions ───────────────────────────────────────────

def show_products_table(products: list[Product]) -> None:
    """Display all products in a styled table — no borders, tonal shifts only."""
    if not products:
        console.print(
            f"[{PRIMARY}]No products tracked yet.[/{PRIMARY}] "
            "Use 'pricewatch add' to start."
        )
        return

    table = Table(
        title="TRACKED PRODUCTS",
        show_header=True,
        header_style=Style(bold=True, color=PRIMARY),
        title_style=STYLE_HEADLINE,
        box=box.SIMPLE_HEAVY,
        show_edge=False,
        pad_edge=True,
        padding=(0, 1),
    )
    table.add_column("ID", style=STYLE_DIM, width=4, justify="right")
    table.add_column("Product", style=STYLE_HEADLINE, max_width=30)
    table.add_column("Current", justify="right")
    table.add_column("Previous", justify="right", style="dim")
    table.add_column("Change", justify="right")
    table.add_column("Trend", min_width=20)
    table.add_column("Status", justify="center", width=3)

    from pricewatch.database import get_price_history

    for p in products:
        change = price_change_text(p.current_price, p.previous_price)
        checked = p.last_checked[:19] if p.last_checked else "Never"

        # Mini sparkline from history
        records = get_price_history(p.id, limit=20)
        if records:
            prices = [r.price for r in reversed(records)]
            spark = build_sparkline(prices, width=20)
        else:
            spark = Text("--", style=STYLE_DIM)

        current_style = STYLE_PRIMARY if (
            p.current_price is not None
            and p.previous_price is not None
            and p.current_price < p.previous_price
        ) else Style(bold=True)

        current_text = Text(format_price(p.current_price), style=current_style)

        table.add_row(
            str(p.id),
            p.name,
            current_text,
            format_price(p.previous_price),
            change,
            spark,
            status_dot(p.last_checked is not None),
        )

    console.print()
    console.print(table)
    console.print()
    console.print(
        Text.assemble(
            ("  ● ", PRIMARY_DIM),
            ("checked   ", "dim"),
            ("○ ", "dim"),
            ("pending", "dim"),
        )
    )
    console.print()


def show_price_history_chart(product: Product, records: list[PriceRecord]) -> None:
    """Display a Unicode box-drawing price chart with stats."""
    if not records:
        console.print(
            f"[{TERTIARY}]No price history yet.[/{TERTIARY}] "
            "Run 'pricewatch check' first."
        )
        return

    records = list(reversed(records))
    prices = [r.price for r in records]
    labels = [r.checked_at[5:16] for r in records]

    chart_text = build_ascii_chart(prices, labels)

    console.print()
    console.print(Panel(
        chart_text,
        title=f"[bold white]{product.name}[/bold white]",
        subtitle=f"[dim]{len(prices)} data points[/dim]",
        border_style=TERTIARY,
        padding=(1, 2),
    ))

    # Stats row — no borders, just spacing
    min_price = min(prices)
    max_price = max(prices)
    avg_price = sum(prices) / len(prices)
    latest = prices[-1]

    stats = Table(show_header=False, box=None, padding=(0, 3), expand=True)
    stats.add_column("Label", style=STYLE_LABEL)
    stats.add_column("Value", justify="right")
    stats.add_row("Current", Text(format_price(latest), style="bold"))
    stats.add_row("Lowest", Text(format_price(min_price), style=STYLE_PRIMARY))
    stats.add_row("Highest", Text(format_price(max_price), style=STYLE_SECONDARY))
    stats.add_row("Average", format_price(avg_price))

    # Sparkline summary
    spark = build_sparkline(prices)
    stats.add_row("Trend", spark)

    console.print(stats)
    console.print()


def show_alerts(drops: list[tuple[Product, float]]) -> None:
    """Display price drop alerts with Kinetic Terminal styling."""
    if not drops:
        console.print(f"[dim]No price drops detected since the last check.[/dim]")
        return

    console.print()
    console.print(Text("PRICE DROP ALERTS", style=STYLE_PRIMARY))
    console.print()

    table = Table(
        show_header=True,
        header_style=Style(bold=True, color=PRIMARY),
        box=box.SIMPLE_HEAVY,
        show_edge=False,
        pad_edge=True,
        padding=(0, 1),
    )
    table.add_column("ID", width=4, justify="right", style="dim")
    table.add_column("Product", style=STYLE_HEADLINE)
    table.add_column("Was", justify="right", style="dim")
    table.add_column("Now", justify="right")
    table.add_column("Saved", justify="right")
    table.add_column("Drop", justify="right")

    for product, pct in sorted(drops, key=lambda x: x[1]):
        assert product.current_price is not None
        assert product.previous_price is not None
        savings = product.previous_price - product.current_price
        table.add_row(
            str(product.id),
            product.name,
            format_price(product.previous_price),
            Text(format_price(product.current_price), style=STYLE_PRIMARY_BG),
            Text(format_price(savings), style=STYLE_PRIMARY),
            Text(f"{pct:.1f}%", style=STYLE_PRIMARY),
        )

    console.print(table)
    console.print()

"""Export price history to CSV and JSON formats."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from rich.console import Console

from pricewatch.database import get_all_products, get_price_history

console = Console()


def export_csv(output_path: str = "pricewatch_export.csv") -> Path:
    """Export all price history to CSV."""
    path = Path(output_path)
    products = get_all_products()

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "product_id", "product_name", "url", "price", "checked_at"
        ])
        for product in products:
            records = get_price_history(product.id, limit=10000)
            for rec in records:
                writer.writerow([
                    product.id,
                    product.name,
                    product.url,
                    f"{rec.price:.2f}",
                    rec.checked_at,
                ])

    return path


def export_json(output_path: str = "pricewatch_export.json") -> Path:
    """Export all price history to JSON."""
    path = Path(output_path)
    products = get_all_products()

    data = []
    for product in products:
        records = get_price_history(product.id, limit=10000)
        data.append({
            "id": product.id,
            "name": product.name,
            "url": product.url,
            "css_selector": product.css_selector,
            "current_price": product.current_price,
            "history": [
                {"price": r.price, "checked_at": r.checked_at}
                for r in records
            ],
        })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return path

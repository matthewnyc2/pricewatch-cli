"""SQLite database layer for price history storage."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Generator

DB_PATH = Path.home() / ".pricewatch" / "pricewatch.db"


@dataclass
class Product:
    id: int
    name: str
    url: str
    css_selector: str
    current_price: float | None
    previous_price: float | None
    last_checked: str | None
    created_at: str


@dataclass
class PriceRecord:
    id: int
    product_id: int
    price: float
    checked_at: str


def _ensure_db_dir() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections."""
    _ensure_db_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                css_selector TEXT NOT NULL,
                current_price REAL,
                previous_price REAL,
                last_checked TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                price REAL NOT NULL,
                checked_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_price_history_product
                ON price_history(product_id, checked_at);
        """)


def add_product(name: str, url: str, css_selector: str) -> int:
    """Add a new product to track. Returns the product ID."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO products (name, url, css_selector) VALUES (?, ?, ?)",
            (name, url, css_selector),
        )
        return cursor.lastrowid  # type: ignore[return-value]


def get_all_products() -> list[Product]:
    """Get all tracked products."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, url, css_selector, current_price, previous_price, "
            "last_checked, created_at FROM products ORDER BY id"
        ).fetchall()
        return [Product(**dict(row)) for row in rows]


def get_product(product_id: int) -> Product | None:
    """Get a single product by ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, url, css_selector, current_price, previous_price, "
            "last_checked, created_at FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
        return Product(**dict(row)) if row else None


def update_price(product_id: int, price: float) -> None:
    """Update product price and insert history record."""
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    with get_connection() as conn:
        # Get current price to set as previous
        row = conn.execute(
            "SELECT current_price FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if row is None:
            return
        previous = row["current_price"]

        conn.execute(
            "UPDATE products SET current_price = ?, previous_price = ?, last_checked = ? "
            "WHERE id = ?",
            (price, previous, now, product_id),
        )
        conn.execute(
            "INSERT INTO price_history (product_id, price, checked_at) VALUES (?, ?, ?)",
            (product_id, price, now),
        )


def get_price_history(product_id: int, limit: int = 50) -> list[PriceRecord]:
    """Get price history for a product, newest first."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, product_id, price, checked_at FROM price_history "
            "WHERE product_id = ? ORDER BY checked_at DESC LIMIT ?",
            (product_id, limit),
        ).fetchall()
        return [PriceRecord(**dict(row)) for row in rows]


def get_price_drops() -> list[tuple[Product, float]]:
    """Get all products where current price < previous price.
    Returns list of (product, percent_change) tuples."""
    products = get_all_products()
    drops: list[tuple[Product, float]] = []
    for p in products:
        if p.current_price is not None and p.previous_price is not None:
            if p.current_price < p.previous_price:
                pct = ((p.current_price - p.previous_price) / p.previous_price) * 100
                drops.append((p, pct))
    return drops


def remove_product(product_id: int) -> bool:
    """Delete a product and its price history. Returns True if deleted."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        return cursor.rowcount > 0

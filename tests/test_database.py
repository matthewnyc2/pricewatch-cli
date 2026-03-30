"""Tests for database module: CRUD operations and price tracking."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pricewatch.database import (
    add_product,
    get_all_products,
    get_price_drops,
    get_price_history,
    get_product,
    init_db,
    remove_product,
    update_price,
)


@pytest.fixture(autouse=True)
def temp_db(tmp_path):
    """Use a temporary database for every test."""
    tmp_db = tmp_path / "test.db"
    with patch("pricewatch.database.DB_PATH", tmp_db):
        init_db()
        yield tmp_db


# ── add_product / get_product ───────────────────────────────────


def test_add_and_get_product():
    pid = add_product("Test Product", "http://example.com", ".price")
    assert pid is not None
    assert isinstance(pid, int)

    product = get_product(pid)
    assert product is not None
    assert product.name == "Test Product"
    assert product.url == "http://example.com"
    assert product.css_selector == ".price"
    assert product.current_price is None
    assert product.previous_price is None


def test_get_nonexistent_product():
    result = get_product(9999)
    assert result is None


# ── update_price ────────────────────────────────────────────────


def test_update_price_first_time():
    pid = add_product("Widget", "http://example.com", ".price")
    update_price(pid, 29.99)

    product = get_product(pid)
    assert product is not None
    assert product.current_price == 29.99
    assert product.previous_price is None


def test_update_price_tracks_previous():
    pid = add_product("Widget", "http://example.com", ".price")
    update_price(pid, 29.99)
    update_price(pid, 24.99)

    product = get_product(pid)
    assert product is not None
    assert product.current_price == 24.99
    assert product.previous_price == 29.99


def test_update_price_sets_last_checked():
    pid = add_product("Widget", "http://example.com", ".price")
    update_price(pid, 10.00)
    product = get_product(pid)
    assert product is not None
    assert product.last_checked is not None


def test_update_price_nonexistent_product():
    """Updating a nonexistent product should silently return."""
    update_price(9999, 10.00)  # Should not raise


# ── price_history ───────────────────────────────────────────────


def test_price_history_ordering():
    pid = add_product("Gadget", "http://example.com", ".price")
    update_price(pid, 100.00)
    update_price(pid, 95.00)
    update_price(pid, 90.00)

    records = get_price_history(pid)
    assert len(records) == 3
    assert records[0].price == 90.00  # newest first
    assert records[-1].price == 100.00


def test_price_history_limit():
    pid = add_product("Gadget", "http://example.com", ".price")
    for i in range(10):
        update_price(pid, 100.0 - i)

    records = get_price_history(pid, limit=3)
    assert len(records) == 3


def test_price_history_empty():
    pid = add_product("Empty", "http://example.com", ".price")
    records = get_price_history(pid)
    assert records == []


# ── price_drops ─────────────────────────────────────────────────


def test_price_drops_detected():
    pid = add_product("Dropping", "http://example.com", ".price")
    update_price(pid, 100.00)
    update_price(pid, 80.00)

    drops = get_price_drops()
    assert len(drops) == 1
    product, pct = drops[0]
    assert pct == pytest.approx(-20.0)


def test_no_drops_when_price_increases():
    pid = add_product("Rising", "http://example.com", ".price")
    update_price(pid, 50.00)
    update_price(pid, 60.00)

    drops = get_price_drops()
    assert len(drops) == 0


def test_no_drops_when_price_unchanged():
    pid = add_product("Stable", "http://example.com", ".price")
    update_price(pid, 50.00)
    update_price(pid, 50.00)

    drops = get_price_drops()
    assert len(drops) == 0


# ── remove_product ──────────────────────────────────────────────


def test_remove_product():
    pid = add_product("Remove Me", "http://example.com", ".price")
    assert remove_product(pid) is True
    assert get_product(pid) is None


def test_remove_nonexistent_product():
    assert remove_product(9999) is False


def test_remove_cascades_history():
    pid = add_product("Cascade", "http://example.com", ".price")
    update_price(pid, 10.00)
    update_price(pid, 20.00)
    remove_product(pid)
    records = get_price_history(pid)
    assert records == []


# ── get_all_products ────────────────────────────────────────────


def test_get_all_products():
    add_product("A", "http://a.com", ".p")
    add_product("B", "http://b.com", ".p")
    products = get_all_products()
    assert len(products) == 2
    assert products[0].name == "A"
    assert products[1].name == "B"


def test_get_all_products_empty():
    products = get_all_products()
    assert products == []

"""Tests for demo module: product seeding and server lifecycle."""

from pathlib import Path
from unittest.mock import patch

import pytest

from pricewatch.database import get_all_products, get_price_history, init_db
from pricewatch.demo import DEMO_DIR, DEMO_PRODUCTS, setup_demo


@pytest.fixture(autouse=True)
def temp_db(tmp_path):
    """Use a temporary database for every test."""
    tmp_db = tmp_path / "test.db"
    with patch("pricewatch.database.DB_PATH", tmp_db):
        init_db()
        yield tmp_db


# ── Demo HTML files ─────────────────────────────────────────────


def test_demo_dir_exists():
    assert DEMO_DIR.exists(), f"Demo directory missing: {DEMO_DIR}"


def test_demo_html_files_exist():
    for item in DEMO_PRODUCTS:
        path = DEMO_DIR / item["file"]
        assert path.exists(), f"Missing demo HTML: {path}"


def test_demo_html_contains_price_element():
    """Each demo HTML must contain the CSS selector target."""
    for item in DEMO_PRODUCTS:
        path = DEMO_DIR / item["file"]
        html = path.read_text(encoding="utf-8")
        selector = item["selector"]
        # Convert CSS selector to a simple check
        if selector.startswith("."):
            class_name = selector[1:]
            assert f'class="{class_name}"' in html or f"class='{class_name}'" in html, (
                f"{item['file']} missing class '{class_name}'"
            )
        elif selector.startswith("#"):
            id_name = selector[1:]
            assert f'id="{id_name}"' in html or f"id='{id_name}'" in html, (
                f"{item['file']} missing id '{id_name}'"
            )


# ── Demo product config ────────────────────────────────────────


def test_demo_products_have_required_fields():
    for item in DEMO_PRODUCTS:
        assert "name" in item
        assert "file" in item
        assert "selector" in item
        assert "prices" in item
        assert len(item["prices"]) >= 2, f"{item['name']} needs at least 2 price points"


# ── setup_demo seeding ──────────────────────────────────────────


def test_setup_demo_creates_products():
    setup_demo()
    products = get_all_products()
    assert len(products) == len(DEMO_PRODUCTS)


def test_setup_demo_seeds_history():
    setup_demo()
    products = get_all_products()
    for product, config in zip(products, DEMO_PRODUCTS):
        records = get_price_history(product.id, limit=100)
        assert len(records) == len(config["prices"])


def test_setup_demo_sets_current_price():
    setup_demo()
    products = get_all_products()
    for product, config in zip(products, DEMO_PRODUCTS):
        assert product.current_price == config["prices"][-1]

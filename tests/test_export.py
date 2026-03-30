"""Tests for export module: CSV and JSON output."""

import csv
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pricewatch.database import add_product, init_db, update_price
from pricewatch.export import export_csv, export_json


@pytest.fixture(autouse=True)
def temp_db(tmp_path):
    """Use a temporary database for every test."""
    tmp_db = tmp_path / "test.db"
    with patch("pricewatch.database.DB_PATH", tmp_db):
        init_db()
        yield tmp_db


# ── CSV export ──────────────────────────────────────────────────


def test_export_csv_creates_file(tmp_path):
    add_product("Widget", "http://example.com", ".price")
    out = tmp_path / "out.csv"
    result = export_csv(str(out))
    assert result == out
    assert out.exists()


def test_export_csv_headers(tmp_path):
    add_product("Widget", "http://example.com", ".price")
    out = tmp_path / "out.csv"
    export_csv(str(out))

    with open(out, encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
    assert headers == ["product_id", "product_name", "url", "price", "checked_at"]


def test_export_csv_data_rows(tmp_path):
    pid = add_product("Widget", "http://example.com", ".price")
    update_price(pid, 29.99)
    update_price(pid, 24.99)

    out = tmp_path / "out.csv"
    export_csv(str(out))

    with open(out, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    # header + 2 data rows
    assert len(rows) == 3
    assert rows[1][1] == "Widget"


def test_export_csv_empty_db(tmp_path):
    out = tmp_path / "out.csv"
    export_csv(str(out))
    with open(out, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert len(rows) == 1  # header only


# ── JSON export ─────────────────────────────────────────────────


def test_export_json_creates_file(tmp_path):
    add_product("Gadget", "http://example.com", ".cost")
    out = tmp_path / "out.json"
    result = export_json(str(out))
    assert result == out
    assert out.exists()


def test_export_json_structure(tmp_path):
    pid = add_product("Gadget", "http://example.com", ".cost")
    update_price(pid, 99.99)

    out = tmp_path / "out.json"
    export_json(str(out))

    with open(out, encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, list)
    assert len(data) == 1
    item = data[0]
    assert item["name"] == "Gadget"
    assert item["url"] == "http://example.com"
    assert item["css_selector"] == ".cost"
    assert item["current_price"] == 99.99
    assert isinstance(item["history"], list)
    assert len(item["history"]) == 1
    assert item["history"][0]["price"] == 99.99


def test_export_json_empty_db(tmp_path):
    out = tmp_path / "out.json"
    export_json(str(out))
    with open(out, encoding="utf-8") as f:
        data = json.load(f)
    assert data == []


def test_export_json_multiple_products(tmp_path):
    pid1 = add_product("A", "http://a.com", ".p")
    pid2 = add_product("B", "http://b.com", ".p")
    update_price(pid1, 10.00)
    update_price(pid2, 20.00)

    out = tmp_path / "out.json"
    export_json(str(out))

    with open(out, encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 2

"""Tests for CLI commands via Typer CliRunner."""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from pricewatch.cli import app
from pricewatch.database import add_product, get_product, init_db, update_price

runner = CliRunner()


@pytest.fixture(autouse=True)
def temp_db(tmp_path):
    """Use a temporary database for every test."""
    tmp_db = tmp_path / "test.db"
    with patch("pricewatch.database.DB_PATH", tmp_db):
        init_db()
        yield tmp_db


# ── version ─────────────────────────────────────────────────────


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "pricewatch" in result.output
    assert "v" in result.output


# ── add ─────────────────────────────────────────────────────────


def test_add_product():
    result = runner.invoke(app, ["add", "http://example.com", ".price", "-n", "Test"])
    assert result.exit_code == 0
    assert "Product added" in result.output
    assert "Test" in result.output


def test_add_product_default_name():
    result = runner.invoke(app, ["add", "http://example.com", ".price"])
    assert result.exit_code == 0
    assert "Unnamed Product" in result.output


# ── list ────────────────────────────────────────────────────────


def test_list_empty():
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "No products tracked" in result.output


def test_list_with_products():
    add_product("Widget", "http://example.com", ".price")
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Widget" in result.output


# ── check ───────────────────────────────────────────────────────


def test_check_empty():
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert "No products to check" in result.output


def test_check_with_mock_scraper():
    add_product("Test", "http://example.com", ".price")
    with patch("pricewatch.cli.scrape_price", return_value=29.99):
        result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert "29.99" in result.output
    assert "1 updated" in result.output


def test_check_scrape_failure():
    add_product("Test", "http://example.com", ".price")
    with patch("pricewatch.cli.scrape_price", return_value=None):
        result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert "FAILED" in result.output
    assert "1 failed" in result.output


# ── history ─────────────────────────────────────────────────────


def test_history_not_found():
    result = runner.invoke(app, ["history", "999"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_history_no_records():
    pid = add_product("Empty", "http://example.com", ".price")
    result = runner.invoke(app, ["history", str(pid)])
    assert result.exit_code == 0
    assert "No price history" in result.output


def test_history_with_data():
    pid = add_product("Charted", "http://example.com", ".price")
    update_price(pid, 100.00)
    update_price(pid, 90.00)
    update_price(pid, 95.00)
    result = runner.invoke(app, ["history", str(pid)])
    assert result.exit_code == 0
    assert "Charted" in result.output


# ── alerts ──────────────────────────────────────────────────────


def test_alerts_none():
    result = runner.invoke(app, ["alerts"])
    assert result.exit_code == 0
    assert "No price drops" in result.output


def test_alerts_with_drop():
    pid = add_product("Dropping", "http://example.com", ".price")
    update_price(pid, 100.00)
    update_price(pid, 80.00)
    result = runner.invoke(app, ["alerts"])
    assert result.exit_code == 0
    assert "Dropping" in result.output


# ── export ──────────────────────────────────────────────────────


def test_export_csv(tmp_path):
    pid = add_product("Exported", "http://example.com", ".price")
    update_price(pid, 50.00)
    out = str(tmp_path / "out.csv")
    result = runner.invoke(app, ["export", "-f", "csv", "-o", out])
    assert result.exit_code == 0
    assert "Exported" in result.output


def test_export_json(tmp_path):
    pid = add_product("Exported", "http://example.com", ".price")
    update_price(pid, 50.00)
    out = str(tmp_path / "out.json")
    result = runner.invoke(app, ["export", "-f", "json", "-o", out])
    assert result.exit_code == 0


def test_export_unknown_format():
    result = runner.invoke(app, ["export", "-f", "xml"])
    assert result.exit_code == 1
    assert "Unknown format" in result.output


# ── remove ──────────────────────────────────────────────────────


def test_remove_product():
    pid = add_product("Bye", "http://example.com", ".price")
    result = runner.invoke(app, ["remove", str(pid)])
    assert result.exit_code == 0
    assert "Removed" in result.output
    assert get_product(pid) is None


def test_remove_not_found():
    result = runner.invoke(app, ["remove", "999"])
    assert result.exit_code == 1
    assert "not found" in result.output

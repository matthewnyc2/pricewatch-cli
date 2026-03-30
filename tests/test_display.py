"""Tests for display module: formatting, sparklines, charts, tables."""

import pytest
from rich.text import Text

from pricewatch.display import (
    build_ascii_chart,
    build_sparkline,
    format_price,
    price_change_text,
    status_dot,
)


# ── format_price ────────────────────────────────────────────────


class TestFormatPrice:
    def test_normal(self):
        assert format_price(29.99) == "$29.99"

    def test_large(self):
        assert format_price(1299.99) == "$1,299.99"

    def test_zero(self):
        assert format_price(0.0) == "$0.00"

    def test_none(self):
        assert format_price(None) == "--"


# ── price_change_text ───────────────────────────────────────────


class TestPriceChangeText:
    def test_decrease(self):
        result = price_change_text(80.0, 100.0)
        assert isinstance(result, Text)
        plain = result.plain
        assert "-20.00" in plain
        assert "-20.0%" in plain

    def test_increase(self):
        result = price_change_text(120.0, 100.0)
        plain = result.plain
        assert "+20.00" in plain
        assert "+20.0%" in plain

    def test_no_change(self):
        result = price_change_text(100.0, 100.0)
        assert "0.00" in result.plain

    def test_none_current(self):
        result = price_change_text(None, 100.0)
        assert result.plain == "--"

    def test_none_previous(self):
        result = price_change_text(100.0, None)
        assert result.plain == "--"

    def test_previous_zero(self):
        result = price_change_text(10.0, 0)
        assert result.plain == "--"


# ── build_sparkline ─────────────────────────────────────────────


class TestBuildSparkline:
    def test_empty_list(self):
        result = build_sparkline([])
        assert result.plain == "--"

    def test_single_value(self):
        result = build_sparkline([42.0])
        assert "42.00" in result.plain

    def test_two_values(self):
        result = build_sparkline([10.0, 20.0], width=10)
        assert len(result.plain) == 10

    def test_flat_values(self):
        result = build_sparkline([5.0, 5.0, 5.0], width=3)
        # All same value should produce chars (any valid spark char)
        assert len(result.plain) == 3

    def test_ascending(self):
        result = build_sparkline([1.0, 2.0, 3.0, 4.0, 5.0], width=5)
        # Last char should be the tallest block
        assert result.plain[-1] == "\u2588"  # full block

    def test_descending(self):
        result = build_sparkline([5.0, 4.0, 3.0, 2.0, 1.0], width=5)
        # Last char should be the lowest block
        assert result.plain[-1] == "\u2581"  # lower block


# ── build_ascii_chart ───────────────────────────────────────────


class TestBuildAsciiChart:
    def test_single_point(self):
        result = build_ascii_chart([42.0], ["2024-01-01"])
        assert "42.00" in result

    def test_two_points(self):
        result = build_ascii_chart([10.0, 20.0], ["Jan", "Feb"])
        assert "Jan" in result
        assert "Feb" in result
        assert "\u250c" in result  # top-left corner
        assert "\u2518" in result  # bottom-right corner

    def test_flat_line(self):
        result = build_ascii_chart([50.0, 50.0, 50.0], ["A", "B", "C"])
        assert "$" in result  # y-axis labels present

    def test_contains_data_points(self):
        result = build_ascii_chart([100.0, 50.0, 75.0], ["A", "B", "C"])
        assert "\u25cf" in result  # filled circle data point


# ── status_dot ──────────────────────────────────────────────────


class TestStatusDot:
    def test_active(self):
        result = status_dot(True)
        assert result.plain == "\u25cf"

    def test_inactive(self):
        result = status_dot(False)
        assert result.plain == "\u25cb"

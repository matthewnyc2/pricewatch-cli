"""Tests for scraper module: parse_price, extract_price, fetch_page."""

import pytest

from pricewatch.scraper import extract_price, fetch_page, parse_price


# ── parse_price ─────────────────────────────────────────────────


class TestParsePrice:
    """Contract: parse_price never raises, returns float or None."""

    def test_us_format(self):
        assert parse_price("$1,299.99") == 1299.99

    def test_simple(self):
        assert parse_price("$49.99") == 49.99

    def test_no_symbol(self):
        assert parse_price("199.00") == 199.00

    def test_european_format(self):
        assert parse_price("1.299,99") == 1299.99

    def test_decimal_comma(self):
        assert parse_price("9,99") == 9.99

    def test_empty_string(self):
        assert parse_price("") is None

    def test_none_like_whitespace(self):
        assert parse_price("   ") is None

    def test_text_only(self):
        assert parse_price("Free") is None

    def test_with_currency_word(self):
        assert parse_price("USD 25.50") == 25.50

    def test_gbp_symbol(self):
        assert parse_price("\u00a3199.99") == 199.99

    def test_euro_symbol(self):
        assert parse_price("\u20ac49,99") == 49.99

    def test_thousands_no_decimal(self):
        assert parse_price("$1,000") == 1000.0

    def test_large_number(self):
        assert parse_price("$12,345,678.90") == 12345678.90

    def test_zero(self):
        assert parse_price("$0.00") == 0.0

    def test_negative_sign_stripped(self):
        # The minus sign is stripped as a non-numeric char, yielding 5.00
        assert parse_price("-$5.00") == 5.0


# ── extract_price ───────────────────────────────────────────────


class TestExtractPrice:
    """Contract: returns float or None, never raises."""

    def test_class_selector(self):
        html = '<div><span class="price">$279.99</span></div>'
        assert extract_price(html, ".price") == 279.99

    def test_id_selector(self):
        html = '<div><span id="cost">$149.00</span></div>'
        assert extract_price(html, "#cost") == 149.00

    def test_missing_element(self):
        html = "<div>No price here</div>"
        assert extract_price(html, ".price") is None

    def test_nested(self):
        html = '''
        <div class="product">
            <span class="product-price">$1,049.99</span>
        </div>'''
        assert extract_price(html, ".product-price") == 1049.99

    def test_empty_html(self):
        assert extract_price("", ".price") is None

    def test_empty_selector(self):
        html = '<span class="price">$10</span>'
        assert extract_price(html, "") is None

    def test_whitespace_html(self):
        assert extract_price("   ", ".price") is None

    def test_element_with_no_text(self):
        html = '<span class="price"></span>'
        assert extract_price(html, ".price") is None

    def test_tag_selector(self):
        html = "<b>$99.00</b>"
        assert extract_price(html, "b") == 99.00


# ── fetch_page ──────────────────────────────────────────────────


class TestFetchPage:
    """Contract: raises ConnectionError on HTTP failure, ValueError on empty URL."""

    def test_empty_url_raises(self):
        with pytest.raises(ValueError, match="URL must not be empty"):
            fetch_page("")

    def test_whitespace_url_raises(self):
        with pytest.raises(ValueError, match="URL must not be empty"):
            fetch_price = fetch_page("   ")

    def test_local_file(self, tmp_path):
        f = tmp_path / "test.html"
        f.write_text("<b>$42.00</b>", encoding="utf-8")
        result = fetch_page(str(f))
        assert "$42.00" in result

    def test_local_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            fetch_page("/nonexistent/file.html")

    def test_file_uri(self, tmp_path):
        f = tmp_path / "page.html"
        f.write_text("<p>hello</p>", encoding="utf-8")
        result = fetch_page(f"file://{f}")
        assert "hello" in result

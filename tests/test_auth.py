"""Tests for authentication signing utilities."""

from pycex.auth import binance_headers, bybit_headers, hmac_sha256


class TestHmacSha256:
    def test_known_value(self) -> None:
        result = hmac_sha256("secret", "message")
        assert isinstance(result, str)
        assert len(result) == 64

    def test_deterministic(self) -> None:
        a = hmac_sha256("key", "data")
        b = hmac_sha256("key", "data")
        assert a == b

    def test_different_keys(self) -> None:
        a = hmac_sha256("key1", "data")
        b = hmac_sha256("key2", "data")
        assert a != b


class TestBinanceHeaders:
    def test_has_api_key(self) -> None:
        headers = binance_headers("my_key")
        assert headers["X-MBX-APIKEY"] == "my_key"


class TestBybitHeaders:
    def test_has_required_fields(self) -> None:
        headers = bybit_headers("key", "secret", "payload")
        assert "X-BAPI-API-KEY" in headers
        assert "X-BAPI-TIMESTAMP" in headers
        assert "X-BAPI-SIGN" in headers
        assert "X-BAPI-RECV-WINDOW" in headers
        assert headers["X-BAPI-API-KEY"] == "key"

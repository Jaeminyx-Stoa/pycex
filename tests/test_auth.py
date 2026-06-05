"""Tests for authentication signing utilities."""

from pycex.auth import binance_headers, bitget_headers, bybit_headers, hmac_sha256


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


class TestBitgetHeaders:
    def test_has_required_fields(self) -> None:
        headers = bitget_headers("key", "secret", "pass", "GET", "/api/v2/spot/account/assets")
        for field in ("ACCESS-KEY", "ACCESS-SIGN", "ACCESS-TIMESTAMP", "ACCESS-PASSPHRASE", "locale", "Content-Type"):
            assert field in headers
        assert headers["ACCESS-KEY"] == "key"
        assert headers["ACCESS-PASSPHRASE"] == "pass"

    def test_demo_flag_adds_paptrading(self) -> None:
        live = bitget_headers("k", "s", "p", "GET", "/x")
        demo = bitget_headers("k", "s", "p", "GET", "/x", demo=True)
        assert "paptrading" not in live
        assert demo["paptrading"] == "1"

    def test_signature_depends_on_path(self) -> None:
        a = bitget_headers("k", "s", "p", "GET", "/a")
        b = bitget_headers("k", "s", "p", "GET", "/b")
        assert a["ACCESS-SIGN"] != b["ACCESS-SIGN"]

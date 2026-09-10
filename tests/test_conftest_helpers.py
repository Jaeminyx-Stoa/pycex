"""Tests for the shared load_fixture() helper and the `live` pytest marker."""

from __future__ import annotations

import httpx
import pytest

from tests.conftest import load_fixture


def test_load_fixture_reads_recorded_json() -> None:
    markets = load_fixture("upbit", "markets")
    assert isinstance(markets, list)
    assert len(markets) == 3
    assert markets[0]["market"].startswith("BTC-") or markets[0]["market"].startswith("KRW-")


def test_load_fixture_raises_for_missing_fixture() -> None:
    with pytest.raises(FileNotFoundError):
        load_fixture("upbit", "does_not_exist")


@pytest.mark.live
def test_live_marker_hits_real_endpoint() -> None:
    """Excluded by default addopts (`-m 'not live'`); only runs with `-m live`."""
    resp = httpx.get("https://api.upbit.com/v1/market/all", params={"is_details": "false"}, timeout=20)
    resp.raise_for_status()
    assert isinstance(resp.json(), list)

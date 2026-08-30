"""Shared test helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(exchange: str, name: str) -> Any:
    return json.loads((FIXTURES / exchange / f"{name}.json").read_text())

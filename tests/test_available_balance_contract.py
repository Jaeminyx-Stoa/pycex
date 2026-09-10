"""A2-5 — ``fetch_available_balance`` 의 base 기본 구현이 무엇을 «보장하지 않는지».

OKX 만 per-currency ``availBal`` 을 실계좌로 측정했다. base 기본 구현은
``Balance.free`` 를 그대로 돌려줄 뿐이고, 다른 6개 거래소에서 그것이
미정산 대금을 제외한다는 근거는 아무도 만든 적이 없다. 그 한계가 docstring 에
적혀 있는지, 그리고 코드가 그 문장을 배신하지 않는지 검사한다.
"""

from __future__ import annotations

import inspect

import pytest

from pycex import OKX, Binance, Bitget, Bithumb, Bybit, Korbit, Upbit
from pycex.base import BaseExchange

# ── A2-5: base 기본 구현의 한계 ──


def test_base_available_balance_docstring_states_the_limit() -> None:
    doc = inspect.getdoc(BaseExchange.fetch_available_balance) or ""
    assert "OKX" in doc
    assert "settlement guarantee" in doc


def test_only_okx_measured_availbal_so_only_okx_overrides() -> None:
    """실제로 «정산 가용»을 측정한 것은 OKX 뿐이다 — 문서와 코드가 같은 말을 한다."""
    assert "fetch_available_balance" in OKX.__dict__
    for cls in (Binance, Bitget, Bithumb, Bybit, Korbit, Upbit):
        assert "fetch_available_balance" not in cls.__dict__, (
            f"{cls.__name__} 이 override 를 추가했다면 base docstring 의 «OKX 외에는 "
            f"보장 없음»이 더 이상 사실이 아니다 — 문서를 함께 고쳐라"
        )


# ── A2-5 우회 거부 ──


@pytest.mark.parametrize(
    "cls", [Binance, Bitget, Bithumb, Bybit, Korbit, OKX, Upbit], ids=lambda c: c.__name__
)
def test_bypass_1_every_override_must_be_documented(cls: type[BaseExchange]) -> None:
    """우회 ① — 조용한 override 로 base 의 경고를 무력화하지 못한다."""
    own = cls.__dict__.get("fetch_available_balance")
    if own is None:
        return
    doc = inspect.getdoc(own) or ""
    assert len(doc) > 80, f"{cls.__name__} 의 override 가 무엇을 측정하는지 적혀 있지 않다"


def test_bypass_2_base_default_is_still_just_free() -> None:
    """우회 ② — «보장된다»고 오해할 만한 계산을 base 에 몰래 넣지 못한다.

    base 는 `Balance.free` 를 그대로 돌려준다. 그 이상을 하는 척하면
    docstring 의 경고가 거짓이 된다.
    """
    src = inspect.getsource(BaseExchange.fetch_available_balance)
    body = src.split('"""')[-1]
    assert "entry.free if entry else 0.0" in body

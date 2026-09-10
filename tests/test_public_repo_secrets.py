"""A2-7 — 공개 레포(PUBLIC)에 비밀값이 실려 나가지 않는다.

기록 픽스처는 **실계좌 6회 실행**에서 뽑았다. 「원장에 인증 헤더가 남지 않는다」는
말만 믿고 넘어가면, 틀렸을 때 되돌릴 수 없다(공개 레포의 히스토리는 지워도 남는다).

그리고 판정기도 틀린다 — 훑개가 «깨끗하다»고 말할 자격이 있는지,
일부러 심은 가짜 비밀값을 잡는지로 먼저 검사한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from secret_scan import scan_repo, scan_text  # noqa: E402


def test_repo_has_no_secrets() -> None:
    hits = scan_repo()
    assert hits == [], "공개 레포에 비밀값처럼 보이는 것이 있다:\n" + "\n".join(hits)


# ── 판정기 검증 (심어서 잡히는지) ──


def test_scanner_catches_a_planted_api_key() -> None:
    planted = '{"apiKey": "a3f9c1d8e7b64205af13cc9d0e2b7a51"}'
    assert scan_text(planted, label="planted") != []


def test_scanner_catches_a_planted_okx_auth_header() -> None:
    planted = '{"OK-ACCESS-PASSPHRASE": "Tr@d3-l1ve-2026-not-a-placeholder"}'
    assert scan_text(planted, label="planted") != []


def test_scanner_catches_a_planted_account_id() -> None:
    planted = '{"acctId": "8813227745901266"}'
    assert scan_text(planted, label="planted") != []


# ── 우회 거부 ──


def test_bypass_1_docs_placeholders_are_not_false_positives() -> None:
    """우회 ① — 오탐이 잦으면 사람이 훑개를 끈다. 문서의 자리표시자는 통과시킨다."""
    docs = 'with OKX(api_key="KEY", secret="SECRET", passphrase="PASS") as ex:'
    assert scan_text(docs, label="docs") == []


def test_bypass_2_a_secret_hidden_in_a_changelog_line_is_still_caught() -> None:
    """우회 ② — 픽스처만 훑고 문서는 안 훑는 식으로 빠져나가지 못한다.

    (``scan_repo`` 의 대상에 CHANGELOG·README·docs 가 들어 있다는 계약.)
    """
    from secret_scan import TARGETS

    names = {p.name for p in TARGETS}
    assert {"fixtures", "CHANGELOG.md", "README.md", "docs"} <= names
    line = "- fixed a thing (api_key=9f2c47ab61de40e8b53a17cd8f0a2e64)"
    assert scan_text(line, label="CHANGELOG.md") != []

"""A2-6 — 뮤테이션 러너. 「초록 = 지킴」이 아니다.

이 라운드의 각 수정을 **하나씩 되돌려** 놓고 테스트를 돌린다. 되돌렸을 때
빨강이 나지 않는 테스트는 아무것도 지키지 않는 테스트다.

    python scripts/mutations_a2.py

원본은 항상 복구한다(실패해도 finally 로). 네트워크 0.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTTP = ROOT / "src" / "pycex" / "http.py"
BASE = ROOT / "src" / "pycex" / "base.py"
CHANGELOG = ROOT / "CHANGELOG.md"

# (라벨, 파일, 찾을 것, 바꿀 것, 빨강이어야 할 테스트)
MUTATIONS: list[tuple[str, pathlib.Path, str, str, list[str]]] = [
    (
        "A2-1 주입 transport 유실 복원 (팩토리를 한 번 쓰고 버린다 = 옛 객체 주입)",
        HTTP,
        """        self._transport_factory = factory
        self._client_obj = None
        self._client_loop = None
""",
        """        self._transport_factory = factory
        self._client_obj = self._new_client()
        self._transport_factory = None
        self._client_loop = None
""",
        ["tests/test_transport_injection.py", "tests/test_shared_http_layer.py"],
    ),
    (
        "A2-2 리미터 무력화 복원 (재빌드마다 새 RateLimiter)",
        HTTP,
        """            self._client_obj = client
        self._client_loop = loop
""",
        """            self._client_obj = client
            self._limiter = RateLimiter(self._rate)
        self._client_loop = loop
""",
        ["tests/test_rate_limit_lifetime.py", "tests/test_shared_http_layer.py"],
    ),
    (
        "A2-1b None 팩토리 거부 제거 (httpx 가 실 transport 로 바꿔치기)",
        HTTP,
        """            if transport is None:""",
        """            if False:""",
        ["tests/test_transport_injection.py", "tests/test_shared_http_layer.py"],
    ),
    (
        "A2-4 CHANGELOG 거짓 문장 복원",
        CHANGELOG,
        "rebuilds the client **and its transport** when",
        "rebuilds client, transport and rate limiter when",
        ["tests/test_changelog_claims.py"],
    ),
    (
        "A2-5 base docstring 의 «보장 없음» 경고 제거",
        BASE,
        "and **nothing verifies that it excludes unsettled\n        proceeds**",
        "and it is a settlement guarantee",
        ["tests/test_available_balance_contract.py"],
    ),
]


def run(paths: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *paths, "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    tail = [ln for ln in proc.stdout.strip().splitlines() if ln.strip()][-1:]
    return proc.returncode, tail[0] if tail else ""


def main() -> int:
    code, line = run(["tests"])
    print(f"[기준] 전체 테스트 → {line}")
    if code != 0:
        print("기준이 이미 빨강이다. 뮤테이션 판정은 의미가 없다.")
        return 1

    failures = 0
    for label, path, find, replace, targets in MUTATIONS:
        original = path.read_text()
        if find not in original:
            print(f"[무효] {label} — 되돌릴 지점을 못 찾았다 (판정기가 틀렸다)")
            failures += 1
            continue
        try:
            path.write_text(original.replace(find, replace, 1))
            code, line = run(targets)
            verdict = "빨강 ✅" if code != 0 else "초록 🚨 (테스트가 아무것도 안 지킨다)"
            print(f"[{verdict}] {label}\n         → {line}")
            if code == 0:
                failures += 1
        finally:
            path.write_text(original)

    code, line = run(["tests"])
    print(f"[복구] 전체 테스트 → {line}")
    if code != 0:
        print("복구 실패 — 원본이 돌아오지 않았다.")
        return 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

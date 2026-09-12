"""Run explicitly: .venv/bin/python tests/mutation_throttle.py

Remove all bucket debits in this process only. The independent mock venue must
reject the adapter overflow sequences, so a green pytest run is a failed mutation
check. Production files are never rewritten and the mutation dies with this process.
"""

from unittest.mock import patch

import pytest

from pycex.ratelimit import _Window


def no_charge(self: _Window, weight: float, now: float) -> None:
    pass


if __name__ == "__main__":
    with patch.object(_Window, "charge", no_charge):
        result = pytest.main([
            "tests/test_throttle_transport.py",
            "-q",
            "-k", "order_overflow_waits_fifo_with_zero_429",
            "--tb=short",
        ])
    if result != pytest.ExitCode.TESTS_FAILED:
        raise SystemExit(f"뮤테이션 실패: 예상한 테스트 RED 대신 종료코드 {result}")
    print("RED 확인됨: 토큰 차감·시간 구간 기록 no-op → 한도 초과 요청에서 429 발생")

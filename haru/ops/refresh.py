#!/usr/bin/env python3
"""대시보드 전체 갱신: 수익(Aside) → 수집 → HTML. 어느 단계가 실패해도 다음 단계는 돈다.

  python3 haru/ops/refresh.py [--no-revenue]
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(name: str, args: list[str]) -> bool:
    r = subprocess.run([sys.executable, str(HERE / name), *args], capture_output=True, text=True, timeout=600)
    print(f"--- {name} (exit {r.returncode})"); print((r.stdout + r.stderr).strip()[-800:])
    return r.returncode == 0


def main() -> int:
    ok = True
    if "--no-revenue" not in sys.argv:
        ok &= run("revenue.py", [])
    run("cf_analytics.py", [])  # 토큰 없으면 건너뜀(실패로 치지 않음)
    ok &= run("collect.py", [])
    ok &= run("build_dashboard.py", [])
    print("[refresh] " + ("완료" if ok else "일부 실패 (위 로그 참고)"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

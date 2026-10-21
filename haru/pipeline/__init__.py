"""하루 파이프라인 — 공통 코드는 공용 코어 **Iris**(`~/EducereProject/sns/core`, 패키지 `iris`, 로이어픽과 공유)에 있고,
이 폴더의 http·queue·threads_client·instagram_client 는 하루 값(경로·UA·고지 검사)을 묶은 얇은 연결부다.
하루만의 것(disclosure 고지, telegram, metrics, imagecheck, report)은 여기 그대로 둔다.
공통 부분을 고칠 땐 코어에서 고치고 `cd ~/EducereProject/sns/core && python3 -m unittest discover -s tests -t .` 를 돌린다.
코어 경로는 환경변수 SNS_CORE 로 바꿀 수 있다.
"""

import os
import sys
from pathlib import Path

_CORE = Path(os.environ.get("SNS_CORE") or Path.home() / "EducereProject" / "sns" / "core")
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from iris import KST  # noqa: E402

__all__ = ["KST"]

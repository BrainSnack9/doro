"""urllib 기반 최소 HTTP 헬퍼 — 공용 코어 iris.http 그 자체다(모듈을 바꿔치기해 `pipeline.http` 와 `iris.http` 가 같은 객체).
테스트가 `pipeline.http.request` 를 패치하면 코어 클라이언트가 그 패치를 본다. dry_run 이면 요청을 출력만 하고 보내지 않는다(토큰 마스킹)."""

import sys

from iris import http as _core

USER_AGENT = "haru-pipeline/0.1 (+stdlib urllib)"
_core.set_user_agent(USER_AGENT)
sys.modules[__name__] = _core

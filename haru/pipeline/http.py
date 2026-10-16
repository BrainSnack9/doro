"""urllib 기반 최소 HTTP 헬퍼. dry_run 이면 요청을 출력만 하고 보내지 않습니다."""

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

USER_AGENT = "haru-pipeline/0.1 (+stdlib urllib)"
TIMEOUT_SEC = 30


def _redact(mapping: Optional[dict]) -> dict:
    """키 이름에 'token'이 들어가면 값을 마스킹합니다."""
    if not mapping:
        return {}
    out = {}
    for k, v in mapping.items():
        out[k] = "***REDACTED***" if "token" in str(k).lower() else v
    return out


def _redact_url(url: str) -> str:
    """경로에 봇 토큰이 들어가는 Telegram 식 URL(/bot<token>/)을 마스킹."""
    parts = urllib.parse.urlsplit(url)
    path = parts.path
    if "/bot" in path:
        head, _, rest = path.partition("/bot")
        token, slash, tail = rest.partition("/")
        path = f"{head}/bot***REDACTED***{slash}{tail}"
    query = urllib.parse.urlencode(_redact(dict(urllib.parse.parse_qsl(parts.query))))
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def request(
    method: str,
    url: str,
    data: Optional[dict] = None,
    params: Optional[dict] = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """HTTP 요청을 보내고 JSON(dict)을 돌려줍니다.

    - data: 폼 인코딩 본문 (POST)
    - params: 쿼리스트링
    - dry_run: 실제 전송 없이 마스킹된 요청을 stdout 에 출력하고 가짜 id 를 반환
    - 실제 모드에서 2xx 가 아니면 응답 본문을 담아 RuntimeError
    """
    method = method.upper()
    full_url = url
    if params:
        sep = "&" if "?" in url else "?"
        full_url = url + sep + urllib.parse.urlencode(params)

    if dry_run:
        shown_url = _redact_url(full_url)
        print(f"[DRY-RUN] {method} {shown_url}")
        if data:
            print("[DRY-RUN]   body: " + json.dumps(_redact(data), ensure_ascii=False))
        digest = hashlib.sha256(f"{method} {full_url} {json.dumps(data, sort_keys=True, ensure_ascii=False)}".encode()).hexdigest()[:12]
        return {"id": f"dryrun-{digest}", "status_code": "FINISHED", "quota_usage": 0}

    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(full_url, data=body, method=method)
    req.add_header("User-Agent", USER_AGENT)
    if body is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} {method} {_redact_url(full_url)}: {err_body}") from None

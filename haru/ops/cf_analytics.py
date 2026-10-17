#!/usr/bin/env python3
"""Cloudflare Web Analytics(허브 harureviews.date) 페이지뷰 → haru/data/cf_analytics.json

토큰: haru/.env 의 CLOUDFLARE_API_TOKEN ("Read analytics and logs" 템플릿, Account Analytics:Read). 없으면 status=no_token 으로 끝낸다.
수집: 최근 7일·30일 페이지뷰(전체, 경로별). go/<slug> 경로 조회수 = 판매처 클릭 수.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARU = HERE.parent
sys.path.insert(0, str(HARU))
from pipeline import KST  # noqa: E402

OUT = HARU / "data" / "cf_analytics.json"
ACCOUNT = "c395027fab6d53a3c3618250cd8f3bd0"
GQL = "https://api.cloudflare.com/client/v4/graphql"


def env() -> dict:
    out = dict(os.environ)
    p = HARU / ".env"
    if p.exists():
        for ln in p.read_text(encoding="utf-8").splitlines():
            if "=" in ln and not ln.strip().startswith("#"):
                k, v = ln.split("=", 1); out.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return out


def gql(token: str, query: str, variables: dict) -> dict:
    req = urllib.request.Request(GQL, data=json.dumps({"query": query, "variables": variables}).encode(), headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
        return json.load(r)


HOST = "harureviews.date"
SITES_QUERY = """
query($account: String!, $since: Time!) {
  viewer { accounts(filter: {accountTag: $account}) {
    sites: rumPageloadEventsAdaptiveGroups(limit: 50, filter: {datetime_geq: $since}) { count dimensions { siteTag requestHost } }
  } }
}
"""


def site_tags(token: str) -> list:
    """Web Analytics 사이트 목록. REST(rum/site_info/list)는 별도 권한이 필요해 GraphQL(최근 90일 pageload 이벤트)로 알아낸다.
    .env 의 CLOUDFLARE_SITE_TAG 가 있으면 그것을 우선 쓴다(아직 조회수가 0인 사이트용)."""
    fixed = env().get("CLOUDFLARE_SITE_TAG", "")
    if fixed:
        return [{"site_tag": fixed, "host": HOST}]
    since = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
    d = gql(token, SITES_QUERY, {"account": ACCOUNT, "since": since})
    if d.get("errors"):
        raise RuntimeError(json.dumps(d["errors"])[:300])
    seen: dict = {}
    for row in d["data"]["viewer"]["accounts"][0]["sites"]:
        tag = row["dimensions"]["siteTag"]; host = row["dimensions"]["requestHost"]
        seen.setdefault(tag, {"site_tag": tag, "host": host, "count": 0})["count"] += row["count"]
    return sorted(seen.values(), key=lambda x: -x["count"])


QUERY = """
query($account: String!, $site: string!, $since: Time!, $until: Time!) {
  viewer { accounts(filter: {accountTag: $account}) {
    total: rumPageloadEventsAdaptiveGroups(limit: 1, filter: {siteTag: $site, datetime_geq: $since, datetime_leq: $until}) { count }
    byPath: rumPageloadEventsAdaptiveGroups(limit: 100, filter: {siteTag: $site, datetime_geq: $since, datetime_leq: $until}, orderBy: [count_DESC]) { count dimensions { requestPath } }
    byDay: rumPageloadEventsAdaptiveGroups(limit: 60, filter: {siteTag: $site, datetime_geq: $since, datetime_leq: $until}, orderBy: [date_ASC]) { count dimensions { date } }
    byReferer: rumPageloadEventsAdaptiveGroups(limit: 20, filter: {siteTag: $site, datetime_geq: $since, datetime_leq: $until}, orderBy: [count_DESC]) { count dimensions { refererHost } }
  } }
}
"""


def collect_window(token: str, site: str, days: int) -> dict:
    until = datetime.now(timezone.utc)
    since = until - timedelta(days=days)
    d = gql(token, QUERY, {"account": ACCOUNT, "site": site, "since": since.strftime("%Y-%m-%dT%H:%M:%SZ"), "until": until.strftime("%Y-%m-%dT%H:%M:%SZ")})
    if d.get("errors"):
        raise RuntimeError(json.dumps(d["errors"])[:300])
    a = d["data"]["viewer"]["accounts"][0]
    total = sum(x["count"] for x in a["total"]) if a["total"] else 0
    paths: dict = {}
    for x in a["byPath"]:
        k = urllib.parse.unquote(x["dimensions"]["requestPath"] or "/")
        paths[k] = paths.get(k, 0) + x["count"]
    go = {p: c for p, c in paths.items() if p.startswith("/go/")}
    return {"days": days, "pageviews": total, "by_path": paths, "go_clicks": go, "go_total": sum(go.values()), "by_day": {x["dimensions"]["date"]: x["count"] for x in a["byDay"]}, "by_referer": {x["dimensions"]["refererHost"] or "(직접)": x["count"] for x in a["byReferer"]}}


def main() -> int:
    tok = env().get("CLOUDFLARE_API_TOKEN", "")
    data = {"collected_at": datetime.now(KST).isoformat(timespec="seconds")}
    if not tok:
        data["status"] = "no_token"
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("[cf] 토큰 없음 (CLOUDFLARE_API_TOKEN) → 건너뜀"); return 0
    try:
        sites = site_tags(tok)
        site = next((s for s in sites if (s.get("host") or "").endswith(HOST)), sites[0] if sites else None)
        if not site:
            raise RuntimeError("Web Analytics 사이트 없음")
        data.update({"status": "ok", "site": site["host"], "w7": collect_window(tok, site["site_tag"], 7), "w30": collect_window(tok, site["site_tag"], 30)})
    except Exception as e:  # noqa: BLE001
        data.update({"status": "error", "error": str(e)[:300]})
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"[cf] {data['status']} " + (f"7일 {data['w7']['pageviews']}뷰 · go 클릭 {data['w7']['go_total']}" if data.get("w7") else data.get("error", "")))
    return 0 if data["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())

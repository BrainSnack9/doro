# 하루 (Haru) — AI 가상 인플루언서 운영 스캐폴드

"하루"는 서울 원룸에 혼자 사는 20대 후반 여성 설정의 **AI 생성 가상인물**입니다.
이 디렉터리는 Claude Code 가 자율로 돌리는 게시 파이프라인의 뼈대입니다.
Python 3.13 표준 라이브러리만 사용하며(urllib/json/hashlib/datetime/argparse/unittest), pip 설치가 없습니다.

## 규정 준수 (하드코딩)
- 모든 게시물 첫 줄: `AI로 생성된 가상인물이 포함된 게시물입니다.`
- 제휴 링크가 있으면 둘째 줄: `이 게시물은 제휴 활동의 일환으로 수수료를 제공받습니다.` (확정형, "받을 수 있습니다" 금지)
- 근거: 공정위 2026-06-01 가이드라인, AI기본법(2026-01). 문구는 `pipeline/disclosure.py` 한 곳에만 있습니다.

## 디렉터리
```
haru/
├── README.md
├── .env.example            # 환경변수 목록 (실값은 절대 커밋 금지)
├── run_daily.py            # 일일 실행 CLI
├── pipeline/
│   ├── __init__.py         # KST 상수
│   ├── disclosure.py       # 고지 문구, compose(), validate_threads_text()
│   ├── http.py             # urllib 래퍼, --dry-run 시 요청 출력(토큰 마스킹)
│   ├── threads_client.py   # Threads API (이미지 게시 + 링크 답글 패턴)
│   ├── instagram_client.py # Instagram Graph API (이미지, 릴스 폴링)
│   ├── telegram_client.py  # Telegram Bot API
│   ├── queue.py            # data/queue.json 콘텐츠 큐
│   ├── metrics.py          # data/metrics.jsonl append-only 지표
│   └── report.py           # daily_report()
├── data/
│   ├── queue.json          # 예시 3건 (product / daily / journal)
│   └── metrics.jsonl       # 실행 시 생성
├── hub/
│   ├── build_hub.py        # links.json + template.html -> dist/index.html
│   ├── links.json          # 제휴 링크 목록 (날짜별)
│   ├── template.html
│   └── dist/index.html     # GitHub Pages 로 배포할 정적 페이지
└── tests/                  # unittest
```

## 환경변수
`.env.example` 참고. 셸에 `export` 로 주입하며 파일로 저장하지 않습니다.

| 변수 | 용도 |
|---|---|
| `THREADS_USER_ID`, `THREADS_ACCESS_TOKEN` | Threads (graph.threads.net/v1.0) |
| `IG_USER_ID`, `IG_ACCESS_TOKEN` | Instagram Graph API (graph.instagram.com/v21.0) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Telegram 봇 (선택) |
| `HUB_BASE_URL` | 링크 허브 URL (Instagram 캡션/프로필에 사용) |

## 실행
`/home/user/doro` 에서:

```bash
# 드라이런: 실제 전송 없이 HTTP 요청을 출력 (토큰은 마스킹)
python3 haru/run_daily.py --dry-run --now 2026-10-17T09:00:00+09:00

# 채널 제한
python3 haru/run_daily.py --dry-run --channels threads,instagram

# 실제 실행 (환경변수 필요)
export THREADS_USER_ID=... THREADS_ACCESS_TOKEN=... ; python3 haru/run_daily.py

# 링크 허브 빌드
python3 haru/hub/build_hub.py

# 일일 리포트
python3 -c "import sys; sys.path.insert(0,'haru'); from pipeline.report import daily_report; daily_report()"

# 테스트
python3 -m unittest discover -s haru/tests -t haru
```

## 일일 실행 흐름
1. `data/queue.json` 을 읽어 `status == pending` 이고 `scheduled_at <= now`(KST) 인 아이템을 고릅니다.
2. 아이템별로 `channels` 에 적힌 채널에 게시합니다.
   - Threads: 제휴 링크 + 이미지 → 이미지 게시 후 `link_attachment` 답글 (이미지 게시물엔 링크를 못 붙이므로). 그 외는 TEXT/IMAGE/VIDEO 단일 게시.
   - Instagram: 이미지 → `media` + `media_publish`; 영상 → REELS 컨테이너 생성 후 `status_code == FINISHED` 폴링 후 게시. 캡션엔 링크 대신 허브 안내.
   - Telegram: `sendPhoto` / `sendMessage` (HTML, 링크 포함 가능).
3. 모든 본문은 `disclosure.compose()` 로 고지 문구가 붙고, Threads 는 `validate_threads_text()` (500자, 링크 5개, AI 라벨) 를 통과해야 합니다.
4. 결과를 `data/metrics.jsonl` 에 추가하고 큐 상태를 `posted|failed` 로 바꿉니다. **pending 이 아닌 아이템은 다시 게시되지 않습니다** (멱등). `--dry-run` 에서는 큐를 저장하지 않습니다.
5. 제휴 링크는 모두 `hub/links.json` 에 모아 `build_hub.py` 로 정적 페이지를 만들어 GitHub Pages 에 올립니다.

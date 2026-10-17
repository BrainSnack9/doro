#!/bin/zsh
# 2026-10-18 하루치 예약 게시 루프: 예약 시각(12:30/19:00/22:00)이 되면 run_daily 가 올리도록 5분마다 실행. 22:40 에 종료.
cd /Users/educere/EducereProject/Project/doro || exit 1
set -a; source haru/.env; set +a
END_TS=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-18 22:40" +%s)
while [ "$(date +%s)" -lt "$END_TS" ]; do
  echo "== $(date '+%F %T')"; python3 haru/run_daily.py 2>&1 | grep -v "access_token" | tail -6
  sleep 300
done
echo "== loop end $(date '+%F %T')"
git add haru/data/queue.json haru/data/metrics.jsonl 2>/dev/null
git -c user.name="_JinseopKim" commit -m "하루 2026-10-18 게시 결과(queue 상태·metrics) 기록

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" >/dev/null 2>&1 && git push origin haru/meta-setup-status >/dev/null 2>&1 && echo "pushed"

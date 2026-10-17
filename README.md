# 하루 (Haru) — AI 가상 인플루언서 운영 저장소

이 저장소는 AI 생성 가상인물 **하루**(@haru.reviews, "하루 | AI 자취생")의 자동 게시 파이프라인만 담습니다.
이전에 같은 저장소에 있던 Doro 타이머 앱 코드는 2026-10-17에 제거했습니다 (git 기록에는 남아 있습니다).

- 코드와 문서는 모두 [`haru/`](haru/) 아래에 있습니다. 시작은 [`haru/README.md`](haru/README.md).
- 오너가 해야 할 설정과 현재 진행 상태: [`haru/docs/OWNER_SETUP.md`](haru/docs/OWNER_SETUP.md)
- 캐릭터 바이블: [`haru/persona.md`](haru/persona.md)
- 링크 허브(GitHub Pages): https://brainsnack9.github.io/doro/ — `haru/hub/build_hub.py`가 만든 정적 페이지를 푸시 때마다 배포합니다.

```bash
# 테스트
python3 -m unittest discover -s haru/tests -t haru

# 드라이런 (실제 전송 없음, 토큰 마스킹)
python3 haru/run_daily.py --dry-run

# 설정 점검 (haru/.env는 git에서 무시됨)
set -a; source haru/.env; set +a; python3 haru/check_setup.py
```

# 오너 설정 가이드 (1회, 약 1시간)

하루가 자동으로 돌아가려면 아래만 사람이 해주면 됩니다. 순서대로. 토큰·비밀번호는 **절대 채팅에 붙여넣지 말고** 4번처럼 환경 설정에 넣어 주세요.

## 1. 계정 만들기 (15분)

| 계정 | 비고 |
|---|---|
| 인스타그램 | 새 계정. 프로필명 `하루 \| AI 자취생`. 설정에서 **프로페셔널 계정(크리에이터)** 으로 전환. 소개 첫 줄: "AI로 만든 가상인물이에요. 써본 척 안 해요." |
| 스레드 | 위 인스타 계정으로 스레드 가입 (자동 연결). |
| 텔레그램 (선택) | 채널 하나 생성 (예: `@haru_deals`). |
| GitHub (선택) | `haru` 저장소를 새로 만들고 Claude에 접근 권한을 주면 코드를 Doro에서 분리해 옮깁니다. 현재 세션은 저장소 생성 권한이 없습니다. |

## 2. Meta 개발자 앱 (20분) — 스레드·인스타 자동 게시의 열쇠

1. https://developers.facebook.com → 로그인 → **내 앱 → 앱 만들기**.
2. 사용 사례에서 **"Threads API 액세스"** 선택 → 앱 이름 `haru-bot` → 만들기.
3. 앱 대시보드 → Threads 사용 사례 → **설정** → 권한 추가: `threads_basic`, `threads_content_publish`, `threads_manage_replies`, `threads_read_replies`, `threads_manage_insights`.
4. **앱 역할 → 역할 → 사람 추가 → "Threads 테스터"** 로 하루 스레드 계정을 추가. 그다음 스레드 앱에서 **설정 → 계정 → 웹사이트 권한** 에 들어가 초대를 **수락**. (이 단계 덕분에 앱 심사 없이 게시가 됩니다.)
5. 같은 사용 사례 설정 화면의 **"사용자 토큰 생성기"** 에서 하루 계정으로 토큰 생성 → 단기 토큰이 나옵니다.
6. 단기 토큰을 60일짜리 장기 토큰으로 바꿉니다 (브라우저 주소창에 입력):
   ```
   https://graph.threads.net/access_token?grant_type=th_exchange_token&client_secret=앱시크릿&access_token=단기토큰
   ```
   앱 시크릿은 앱 대시보드 → 앱 설정 → 기본 설정에 있습니다. 응답의 `access_token`이 장기 토큰입니다. (만료 전 갱신은 Claude가 자동으로 합니다.)
7. 사용자 ID 확인:
   ```
   https://graph.threads.net/v1.0/me?fields=id,username&access_token=장기토큰
   ```
8. 인스타그램도 같은 앱에서: **제품 추가 → Instagram → "Instagram 비즈니스 로그인 설정"** → 권한 `instagram_business_basic`, `instagram_business_content_publish` → 앱 역할에 **Instagram 테스터** 로 하루 계정 추가 → 인스타 앱 설정 → 앱 및 웹사이트 → 테스터 초대 수락 → 토큰 생성 → 장기 교환:
   ```
   https://graph.instagram.com/access_token?grant_type=ig_exchange_token&client_secret=앱시크릿&access_token=단기토큰
   ```
   사용자 ID: `https://graph.instagram.com/v21.0/me?fields=id,username&access_token=장기토큰`

화면 구성이 이 설명과 다르면 스크린샷 대신 "어느 메뉴에서 막혔는지"만 알려 주세요. Meta가 메뉴를 자주 바꿉니다.

## 3. 제휴 프로그램 가입 (15분)

| 프로그램 | 어디서 | 메모 |
|---|---|---|
| 올리브영 쇼핑 큐레이터 | 올리브영 앱/웹 → 쇼핑 큐레이터 신청 | 심사 없음. 활동 채널에 스레드 주소. |
| 오늘의집 큐레이터 | 오늘의집 앱 → 마이페이지 → 큐레이터 | 누구나. 정산 1원부터. |
| 네이버 쇼핑커넥트 | 네이버 쇼핑커넥트 센터 | 채널 1개 등록(스레드 또는 인스타). 사업자 불필요. |
| 쿠팡 파트너스 | https://partners.coupang.com | 보조. 누적 판매 15만 원 전엔 API가 없어 초기 링크는 오너가 사이트에서 직접 생성해 전달. |

가입 시 약관에 "AI·가상인물·자동화" 관련 조항이 있으면 한 줄 알려 주세요. 조사 결과로는 어느 프로그램도 명시 금지는 없었습니다.

## 4. Claude 환경 설정 (10분) — 이게 없으면 자동 게시가 안 됩니다

세션 제목 표시줄의 **클라우드 환경 메뉴 → Edit** 에서:

**Network access → Allowed domains** 에 추가 (Allow package managers는 켠 채로):
```
graph.threads.net
graph.instagram.com
graph.facebook.com
api.telegram.org
d8j0ntlcm91z4.cloudfront.net
static-public-media.higgsfield.ai
cdn.higgsfield.ai
```
현재 정책은 위 호스트 연결을 모두 거부합니다 (2026-10-16 확인). 절차: https://code.claude.com/docs/en/cloud-environments#network-access

**Network secrets (또는 환경 변수)** 에 아래 이름으로 저장:
```
THREADS_USER_ID
THREADS_ACCESS_TOKEN
IG_USER_ID
IG_ACCESS_TOKEN
TELEGRAM_BOT_TOKEN        (선택)
TELEGRAM_CHAT_ID          (선택, 예: @haru_deals)
META_APP_SECRET           (토큰 자동 갱신용)
```
저장 후 새 세션부터 읽힙니다.

## 5. 세무 (첫 정산 전)

제휴 수익은 사업소득으로 3.3% 원천징수됩니다. 사업자등록이 먼저 필요한지는 세무 Q&A에서도 의견이 갈리니, 첫 정산 전에 세무사에게 "플랫폼 제휴 수수료, 개인, 연 예상 수백만 원 이하" 조건으로 한 번만 물어보세요.

## 끝나면

"설정 끝났어"라고만 말해 주세요. Claude가 토큰을 검증하고(게시 한도 조회), 첫 게시물을 **초안으로 보여준 뒤** 승인받고 올립니다. 그 다음부터 매일 06:30 KST 자동 실행.

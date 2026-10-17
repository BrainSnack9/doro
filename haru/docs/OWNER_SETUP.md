# 오너 설정 가이드 (1회, 약 1시간)

하루가 자동으로 돌아가려면 아래만 사람이 해주면 됩니다. 순서대로. 토큰·비밀번호는 **절대 채팅에 붙여넣지 말고** 4번처럼 환경 설정에 넣어 주세요.

## 진행 상태 (2026-10-17, 데스크톱 세션에서 Meta 개발자 화면 직접 확인)

| 항목 | 상태 |
|---|---|
| Meta 앱 `haru-bot` | 생성됨. 앱 ID `1058626380505854`, 모드 "개발 중" |
| Threads API 이용 사례 | 추가됨. Threads 앱 ID `1069022236132699`, 표시 이름 `haru-bot`, 앱 시크릿 발급됨 |
| Threads 권한 5개 (`threads_basic`, `threads_content_publish`, `threads_manage_replies`, `threads_read_replies`, `threads_manage_insights`) | 모두 "테스트 준비 완료" |
| Threads 테스터 | `haru.reviews` 초대 수락 완료 (2026-10-17) |
| Threads 토큰 | 장기 토큰 발급·검증 완료 (2026-10-17, `@haru.reviews`, 게시 한도 0/250). `THREADS_USER_ID` = `39374388438874300`. 로컬 `haru/.env`(git 무시)에 저장됨. 클라우드 Network secrets 저장은 미확인 |
| 사용자 토큰 생성기 | 장기 토큰을 바로 발급함 (2-6의 단기→장기 교환 불필요). 팝업은 브라우저의 스레드 세션 계정으로 진행되므로 **하루 프로필로 로그인된 상태**에서 눌러야 함. 다른 계정이면 `1349245 "has not accepted the invite"` 오류 |
| 리디렉션 콜백 URL | 비어 있음. 토큰 생성기 방식에서는 불필요 |
| Instagram 이용 사례 | 추가됨 (2026-10-17). "Instagram 로그인이 포함된 API 설정" 방식. Instagram 앱 ID `1094923173172427`, 앱 이름 `haru-bot-IG` |
| Instagram 권한 | `instagram_business_basic`, `instagram_business_content_publish`, `instagram_business_manage_messages` 테스트 준비 완료 |
| Instagram 테스터 | `haru.reviews` 초대 수락 완료 (2026-10-17). 계정 유형은 크리에이터(디지털 크리에이터)로 전환 |
| Instagram 토큰 | 계정 연결 완료. `IG_USER_ID` = `27950973734577301` (`/me`가 돌려주는 앱 전용 ID. 대시보드에 보이는 `17841429945473213`은 프로페셔널 계정 ID로, 클라이언트는 전자를 사용). 토큰 검증 결과 `@haru.reviews`, `MEDIA_CREATOR`. 토큰은 Instagram API 설정 화면 "2. 액세스 토큰 생성" 행의 **토큰 생성** 링크로 발급 (오너 보관, Network secrets `IG_ACCESS_TOKEN`) |
| `META_APP_SECRET` | 로컬 `haru/.env`에 저장됨 (토큰 자동 갱신용) |
| 로컬 점검 | `set -a; source haru/.env; set +a; python3 haru/check_setup.py` → **모두 통과** (2026-10-17) |
| 제휴 프로그램 가입 (3번) | 쿠팡 파트너스: 활성 계정 확인 (2026-10-17, 대시보드·상품검색 사용 가능). 파트너스 ID `AF1214137`. 링크는 사이트에서 직접 생성(누적 15만 원 전 API 없음). 네이버 쇼핑커넥트: 독립 사이트가 아니라 **브랜드 커넥트**(brandconnect.naver.com) 안의 기능. 크리에이터 스페이스 개설에 채널 연동 필수(블로그·클립·인스타·유튜브, 스레드 불가). 인스타 연동 조건 = 프로페셔널 계정 + 페이스북 페이지 연결 → 페이지 "하루 AI 자취생"에 `@haru.reviews` 연결 완료(2026-10-17). 연동 시 Facebook 로그인은 페이지 소유자(오너 개인 계정)로. **인스타 연동 통과(2026-10-17)**, 페이스북 비즈니스 통합에 "네이버 채널플러그인" 등록됨. 크리에이터 스페이스 개설 완료(2026-10-17, 스페이스명 "하루 | AI 자취생", 메인 주제 리빙, 서브 뷰티·생활건강). 개설 직후 MY에 쇼핑커넥트 메뉴 없음(2026-10-17). 스페이스 심사 완료 또는 베타 초대 후 "쇼핑 커넥트" 메뉴 → 약관 동의로 시작된다는 외부 안내 있음. 며칠 뒤 MY 재확인, 계속 없으면 브랜드 커넥트 고객센터에 쇼핑커넥트 참여 문의. 올리브영 쇼핑 큐레이터: 웹 마이페이지에는 메뉴 없음 확인(2026-10-17, 로그인 상태에서 쇼핑 활동/마이 월렛/참여·리서치/마이 정보만 존재) → **앱 마이페이지 → "큐레이터 활동으로 수익얻기" → 참여하기**로만 신청. **올리브영 신청 완료(2026-10-17, 앱)**, 10일 이내(~2026-10-27) 회신 예정. 제출 캡처: `haru/assets/proof/instagram-profile-2026-10-17.jpg`. 오늘의집 큐레이터: 앱 마이페이지에서 신청, 미가입 |
| 클라우드 환경 네트워크 허용·환경변수 (4번) | 미확인. `haru/.env`의 다섯 줄(`THREADS_*`, `IG_*`, `META_APP_SECRET`)을 Environment variables에 그대로 붙여넣고, Network access를 Custom + 허용 도메인으로 설정 |
| 인스타·스레드 프로필 | 소개 문구 교체 완료 (2026-10-17). 인스타는 "AI로 생성한 프로필" 라벨 켬, 스레드는 링크 허브를 프로필 링크로 등록. 인스타 웹사이트 칸은 모바일 앱에서만 편집 가능(미입력) |
| 링크 허브 도메인 | `harureviews.date` 구매(Cloudflare, 2026-10-17). GitHub Pages 커스텀 도메인 등록·배포 CNAME·HUB_BASE_URL 교체 완료. Cloudflare DNS: A @ → 185.199.108/109/110/111.153, CNAME www → brainsnack9.github.io, **프록시 끔(DNS only)** 필수. HTTPS 강제는 인증서 발급 후 켬. (`haru.reviews`는 미구매) |

사람 추가·테스터 등록 같은 권한 부여 클릭은 Claude 자동 모드에서 차단되므로 오너가 직접 누르거나 그 클릭만 승인해 주면 됩니다.

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

claude.ai/code 새 세션 화면에서 입력창 바로 아래 첫 컨트롤(환경 선택기) → **Cloud** 아래 환경 행에 마우스를 올려 톱니 아이콘 → **Edit cloud environment**. 돌고 있는 세션에서는 제목 옆 ▾ → **Edit cloud environment**. 거기서:

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

**Environment variables** 칸에 `.env` 형식(`KEY=value`, 한 줄에 하나)으로 저장. Network secrets는 프록시가 헤더를 붙이는 방식이라 세션 안에서 값을 읽을 수 없으므로 쓰지 않는다:
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

# 하루 리뷰 일지 릴스 제작 레시피 (2026-10-20 1편 '전기요' 기준)

인스타는 2026-10-20 오너 결정으로 카드뉴스 대신 **"하루 리뷰 일지" 릴스**를 올린다. 1편은 전부 손으로 만들었고, 이 문서는 그 과정을 매일 작업(haru-daily-post)이 그대로 밟을 수 있게 단계와 보조 스크립트로 정리한 것이다.
힉스필드는 MCP 도구(`generate_image`, `generate_video`, `generate_audio_batch`, `jobs_wait`)로만 부를 수 있으므로 파이썬이 대신 호출하지 못한다. 에이전트가 1~4단계를 직접 밟고, 5단계부터는 스크립트가 맡는다.

참고 파일: 1편 산출물 `haru/assets/reels/2026-10-20-blanket/`(대본 `script.txt`, 장면 계획 `plan.json`, 문장별 음성 `lines/`, 스펙 `spec-lines.json`).

| 단계 | 누가 | 도구 | 산출물 |
|---|---|---|---|
| 0. 재료: 상품·리뷰 | 스크립트 | `coupang_reviews.py` | `reviews.json` |
| 1. 대본 13문장 | 에이전트 | 손 | `script.txt` |
| 2. 키프레임 3장 | 에이전트 | 힉스필드 `generate_image`(soul_2) | `key-*.png` |
| 3. 클립 3개 | 에이전트 | 힉스필드 `generate_video`(kling3_0 pro 5초) | `clip-*.mp4` |
| 4. 문장별 음성 | 에이전트 | 힉스필드 `generate_audio_batch`(elevenlabs Hallie) | `lines/NN.mp3` |
| 5. 음성 다듬기·타임라인 | 스크립트 | `reel_lines.py` | `voice-lines.wav`, `lines/timeline.json` |
| 6. 장면 계획 → 스펙 | 에이전트 + 스크립트 | `plan.json` → `reel_spec.py` | `spec.json` |
| 7. 렌더 | 스크립트 | `reels.py` | `haru/hub/static/reels/<slug>.mp4` |
| 8. 배포·큐 등록 | 에이전트 | `build_hub.py`, git, `queue.json` | 인스타 릴스 게시 |

작업 폴더: `haru/assets/reels/YYYY-MM-DD-<slug>/` (slug 는 상품 한 단어 영문, 예 `blanket`). 큐·스펙의 `slug` 는 `YYYY-MM-DD-<slug>-<판>` (1편 v2 는 `2026-10-20-blanket-3`).

## 0. 재료: 상품과 실제 리뷰

- 상품은 그날 비축(`haru/hub/links.json` 의 `posted: false`)에서 고른다. 쿠팡 제휴 링크(`link.coupang.com/a/...`)와 공식 상품 사진(`image`)이 이미 있다.
- 리뷰는 **실제 문장**만 쓴다. Aside u0 로 쿠팡 상품평 탭을 읽는다:

```bash
python3 haru/tools/coupang_reviews.py "https://link.coupang.com/a/XXXX" --out haru/assets/reels/YYYY-MM-DD-slug/reviews.json
```

  쿠팡 홈 → 같은 탭에서 링크 이동 → "상품평" 탭 순서로 열어야 "사용권한이 없습니다"를 피한다(스크립트가 처리). 결과는 `best`(베스트순) 목록 `{name, date, stars, text, header}`. 닉네임은 가려져 나온다(윤*기, 엄***). 출력의 `header` 가 상품명·옵션이고 `text` 가 본문인지 눈으로 한 번 확인하고, 본문이 상품명으로 시작하면 `--name "<리뷰 머리말의 상품명(모델명까지)>"` 로 다시 돌린다.
- 상품 사진 3장: 판매처 상세 이미지에서 **정사각형**으로 잘라 `detail-*.jpg` 로 저장(`reels.py` 의 product 장면은 정사각 카드). 하루 사진에 제품을 그리지 않는 규칙(character.json `no_product_rule`)은 릴스에도 그대로: 실물은 판매처 사진으로만.

## 1. 대본: 13문장 안팎, 50초 안쪽

말투는 `haru/persona.md` 그대로(반말, 열 자 안팎으로 끊기, ㅋㅋ 1~2번, "써보니" 금지). 구조는 1편과 같다:

1. 훅 1~2문장(그날의 불평·궁금증. "바닥난방 켜기엔 아깝고, 안 켜기엔 추운 10월.")
2. 하루의 사정 농담 + 리뷰를 읽었다는 사실·숫자("나야 체온이 없어서 상관없는데, 궁금해서 상품평 7만 4천 개를 읽음.")
3. "사람들이 젤 많이 한 말, 세 개만."
4. 하나·둘·셋: 각 2문장(주장 + 근거 숫자나 재구매 언급). **셋은 단점**("근데 단점.") + 별점 낮은 쪽 이유 + 긴 리뷰 공통 경고.
5. 가격·배송·사이즈 한 문장. 마지막 "리뷰 읽고 고른 건 프로필 링크에."

**문장 분할 규칙**(한 줄 = 음성 한 조각 = 자막 한 장):
- 한 줄은 숨 한 번에 읽는 길이(한글 12~28자). 쉼표로 이어지는 긴 문장은 쉼표에서 줄을 나누고 **앞 줄 끝에 쉼표를 남긴다**(쉼이 0.3초로 짧아짐).
- "하나. 성능에 비해 싸다. 열에 여섯이 이걸 눌렀음." 처럼 번호·주장·근거는 **한 줄**에 둔다(카드 1·2장이 이 줄 안에 뜬다).
- 숫자는 말하듯이 적는다("2만 9천 8백 원", "7만 4천 개"). 영문 약자는 음성 엔진이 읽는 대로 확인(L, cm).
- 줄 끝 탭 + 숫자로 그 줄 뒤 쉼(초)을 직접 정할 수 있다. 1편은 문단 앞(하나·둘·셋·가격) 0.6, 문단 안 0.35, 쉼표 뒤 0.25~0.3 으로 손질했다. 기본값은 마침표 0.55 / 쉼표 0.3.

`script.txt` 에 한 줄 = 한 문장으로 저장한다('#' 줄은 주석).

## 2. 키프레임 3장 (힉스필드 generate_image, soul_2)

`haru/assets/character.json` → `higgsfield.daily_image_recipe` 를 따른다. 1편 호출값:

```
model: soul_2, soul_id: <character.json soul_id>, aspect_ratio: "9:16", quality: "1.5k"
prompt: <scene_prefix> + ". " + <scene_variants 의 prompt 한 개를 릴스용으로 다듬은 문장> + ", vertical full-body framing with room around her, natural low light, slight grain, no text, no product."
```

- **prefix 는 그대로**(한국 원룸 단서: 흰 PVC 샤시창+방충망, 벽걸이 에어컨, 흰 벽지, 강화마루, 빌트인 옷장, 창밖 빌라·전봇대). `avoid` 목록은 **프롬프트에 쓰지 않고** 결과 검수 체크리스트로만(적으면 오히려 그려진다).
- 장면 3개는 `scene_variants` 에서 서로 다른 key 3개(1편: `bed_edge` 훅 → `window` 전개 → `desk` 마무리). 시간대·자세·옷이 셋 다 다르게. 세로 9:16 이므로 "vertical framing", "full-body/waist up" 을 적는다.
- 제품 이름·형태 금지, "no product" 를 끝에 둔다. 얼굴이 정면 클로즈업이면 AI 티가 나므로 측면·반뒷모습·눈높이.
- 검수: 북미 아파트 단서(벽돌·목창·라디에이터·카펫), 영어 책등, 손에 든 물건. 실패하면 같은 key 로 한 번 더, 두 번 실패면 다른 key.
- 결과 PNG 를 `key-<key>.png` 로 저장하고 `jobs_wait` 로 받은 **media id** 를 적어 둔다(3단계 `start_image` 에 쓴다).

## 3. 클립 3개 (힉스필드 generate_video, kling3_0 pro 5초, 8.75크레딧/컷)

```
model: kling3_0, aspect_ratio: "9:16", duration: 5, mode: "pro", sound: "off"
medias: [{"value": "<키프레임 media id>", "role": "start_image"}]
prompt 템플릿:
  "Realistic handheld smartphone video, <카메라: static framing with tiny natural hand shake | very slow push-in | slow gentle dolly in toward the desk>.
   The young woman <장면 속 작은 동작 두세 개: keeps scrolling her phone slowly, her thumb moves, she smiles a little at the screen and pulls the duvet closer>.
   <빛·창밖은 그대로: warm bedside lamp light steady, night outside the window>.
   No camera moves(또는 위 카메라와 맞게), no new objects, no text, natural subtle motion only."
```

- 프리셋이 붙으면 `declined_preset_id` 로 거절하고 프롬프트 그대로 생성(1편에서 두 번 그랬다).
- 새 물건·글자·큰 몸동작을 금지하는 문구를 꼭 넣는다. 클립은 5초지만 `reels.py` 가 장면 길이에 맞춰 슬로모션(최소 0.45배)으로 늘리니 한 장면 11초까지는 버틴다.
- `clip-<key>.mp4` 로 저장. 생성 전 `get_cost: true` 로 비용을 한 번 확인한다.

## 4. 문장별 음성 (힉스필드 generate_audio_batch, elevenlabs Hallie)

```
model: "text2speech_v2", variant: "elevenlabs", voice_type: "preset",
voice_id: "10274bf1-fb93-554f-b59f-d620a920fd36"   # Hallie — 2026-10-20 오너가 6개 시안 중 고름
prompt: <대본 한 줄 그대로>
```

- **한 문장 = 요청 하나**로 `generate_audio_batch` 에 13건을 넣는다(통째로 만들면 자막·카드 시각을 맞출 수 없다. 1편 v1 이 그래서 삭제·재게시됨). 배치 한도에 걸리면 나머지는 `generate_audio` 로 따로.
- 결과 mp3 를 `lines/01.mp3`, `lines/02.mp3` … 대본 줄 순서대로 저장한다(이름 정렬 = 줄 순서).
- 원본은 1.0배 속도로 받고 배속은 5단계에서 한다(엔진 속도 옵션보다 ffmpeg 쪽이 균일).

## 5. 다듬기·이어 붙이기·타임라인 (reel_lines.py)

```bash
python3 haru/tools/reel_lines.py haru/assets/reels/YYYY-MM-DD-slug/script.txt haru/assets/reels/YYYY-MM-DD-slug/lines \
  --out haru/assets/reels/YYYY-MM-DD-slug/voice-lines.wav
```

문장마다 앞뒤 무음 제거(-40dB, 0.05초) → 1.22배속 → `lines/NN.wav`, 쉼을 넣어 이은 `voice-lines.wav`, 문장 시작·끝이 적힌 `lines/timeline.json`. 1편 산출물(`lines/`, `timeline.json`)과 바이트 단위로 같다. 총 길이가 55초를 넘으면 대본을 줄인다(릴스는 60초 안쪽이 목표, `reels.py` 상한 90초).

## 6. 장면 계획 → 스펙 (plan.json → reel_spec.py)

`plan.json` 은 "어느 문장 구간에 무엇을 보여줄지"만 적고 초 단위 계산은 스크립트가 한다. 시각 표기: `"L5"` = 5번 문장 시작(자막·머리말·카드는 0.12초 먼저, 장면 경계·until 은 0.10초 먼저), `"L5+1.0"` = 5번 문장 시작 + 1초, `"L5e"` = 5번 문장 끝, `"S4"` = 4번 장면 시작, `"end"` = 내레이션 끝 + tail, 숫자 = 초.

```json
{
 "slug": "2026-10-21-xxx-1", "series": "하루 리뷰 일지", "bottom": "하루 리뷰 일지 #2 · 상품",
 "audio": "haru/assets/reels/2026-10-21-xxx/voice-lines.wav",
 "music": "haru/assets/reels/music/mixkit-135.mp3", "music_db": -23, "tail": 1.0,
 "timeline": "haru/assets/reels/2026-10-21-xxx/lines/timeline.json",
 "scenes": [
  {"kind": "video", "src": ".../clip-bed.mp4"},
  {"kind": "video", "src": ".../clip-window.mp4", "start": "L3"},
  {"kind": "video", "src": ".../clip-desk.mp4", "start": "L4"},
  {"kind": "product", "src": ".../detail-1.jpg", "start": "L5", "zoom": "in"},
  {"kind": "product", "src": ".../detail-2.jpg", "start": "L7", "zoom": "out"},
  {"kind": "product", "src": ".../detail-3.jpg", "start": "L9", "zoom": "in"},
  {"kind": "video", "src": ".../clip-bed.mp4", "start": "L12"}
 ],
 "captions": [
  {"at": "L1", "lines": ["바닥난방 켜기엔 아깝고", "*안 켜기엔 추운 10월"], "size": 80, "pos": "upper"},
  {"at": "S4", "lines": []},
  {"at": "L12", "lines": ["*2만 9천 8백 원 · 내일 도착", "1인용 폭이라 더블이면 L"], "size": 66, "pos": "upper"},
  {"at": "L13", "lines": ["리뷰 읽고 고른 건", "*프로필 링크에"], "size": 82, "pos": "center"}
 ],
 "pills": [
  {"from": "L5", "until": "S5", "text": "① 성능에 비해 싸다"},
  {"from": "L7", "until": "S6", "text": "② 이불처럼 얇다"},
  {"from": "L9", "until": "S7", "text": "③ 근데 단점"}
 ],
 "cards": [
  {"group": 1, "at": "L5+1.0", "name": "잡**", "date": "2026.05.04", "text": "리뷰 실제 문장"},
  {"group": 1, "at": "L5+3.1", "name": "오**", "date": "2026.10.07", "text": "리뷰 실제 문장"},
  {"group": 1, "at": "L6", "kind": "summary", "name": "하루", "text": "하루 메모(요약·숫자)"},
  {"group": 3, "at": "L9+1.6", "kind": "summary", "name": "하루", "text": "단점은 하루 메모로"}
 ]
}
```

규칙:
- **장면**: 훅 구간(1~4번 문장)은 하루 클립 3개, 하나·둘·셋 구간은 상품 사진 3장(zoom in/out 번갈아), 마지막 가격·링크 문장은 첫 클립으로 돌아온다. 1편은 첫 두 경계만 손으로 초를 적었다(5.9, 11.02: 클립 호흡에 맞춤).
- **자막**: 훅·가격·마무리 문장만 큰 자막(2~3줄, `*` 줄은 형광펜 강조). 상품 사진 구간은 `{"at": "S4", "lines": []}` 로 자막을 끈다(머리말·카드가 대신한다).
- **머리말(pills)**: 하나·둘·셋 문장 시작에 "① …" 띠, until 은 다음 구간 장면 시작.
- **카드 선정**: 구간마다 3장. ① ② 는 **리뷰 실제 문장 2장 + 하루 메모 1장**(요약·숫자). ③ 단점 구간은 리뷰를 고르지 말고 **하루 메모 3장**(단점·낮은 별점 이유·주의사항). 리뷰 카드는 `reviews.json` 의 `text` 를 한 문장(40자 안팎, 3줄 이내)으로 자르되 **말을 바꾸지 않는다**. 이름·날짜는 스크립트가 준 가린 값 그대로. 카드 시각은 문장 번호 + 오프셋(`L5+1.0`, `L5+3.1`, 다음 문장 `L6`)으로 2초 간격쯤.
- `kind: "summary"` 카드는 버터색 + '하루 메모' 칩으로 렌더된다. `source` 를 주면 출처 칩 문구가 바뀐다(기본 "쿠팡 상품평").

```bash
python3 haru/tools/reel_spec.py haru/assets/reels/YYYY-MM-DD-slug/plan.json      # → 같은 폴더 spec.json, 경계 불일치·파일 없음·카드 늦음 경고
python3 haru/tools/reels.py haru/assets/reels/YYYY-MM-DD-slug/spec.json          # → haru/hub/static/reels/<slug>.mp4
```

렌더 후 `reels.py --keep-tmp` 로 자막·카드 PNG 를 보거나 mp4 를 열어 글자 잘림·카드 겹침을 확인한다. 카드 본문은 3줄까지만 그려지니 긴 문장은 자른다.

## 7~8. 배포와 큐 등록

1. `python3 haru/hub/build_hub.py` → `haru/hub/dist/reels/<slug>.mp4` 복사.
2. `git add haru/assets/reels/YYYY-MM-DD-slug haru/hub/static/reels haru/hub/dist haru/data/queue.json` → 커밋 → push → PR(base `ccr-f12c0d22-7a4l0e`) → 체크 통과 시 머지(오너 상시 승인). 머지 후 1~2분 뒤 `https://harureviews.date/reels/<slug>.mp4` 가 200 이 될 때까지 `curl -s -o /dev/null -w "%{http_code}"` 로 기다린다.
3. 큐 아이템(1편 v2 `2026-10-20-blanket-instagram-v2` 참고): `channels: ["instagram"]`, `video_url: "https://harureviews.date/reels/<slug>.mp4"`, `image_url`(표지용 하루 사진), `affiliate`, `hashtags`(상품 2~4개 + 기본 6개는 자동), `reel: {"spec": "<spec.json 경로>", "series": "하루 리뷰 일지", "no": N}`, `scheduled_at` 19:00. 본문은 스레드 제품 글과 같은 글. `run_daily` 가 `video_url` 이 있으면 `post_reel`(REELS 컨테이너 → FINISHED 폴링)로 올린다.
4. 게시 뒤 `links.json` 의 `posted`·`date` 갱신과 허브 재빌드는 제품 글과 같다.

## 크레딧 예산 (한 편 약 30~35)

| 항목 | 단가 | 수량 | 소계 |
|---|---|---|---|
| 키프레임 soul_2 1.5k | 0.12 | 3 | 0.36 |
| 클립 kling3_0 pro 5초 | 8.75 | 3 | 26.25 |
| 음성 elevenlabs 13문장 | 문장당 소액(길이 비례) | 13 | 수 크레딧 |
| 재생성 여유 | | | 키프레임 1~2장 |

클립이 거의 전부다. 클립을 다시 뽑는 일은 피하고(키프레임 검수를 먼저 꼼꼼히), 비용은 `get_cost: true` 로 확인한 뒤 생성한다. 음악은 `haru/assets/reels/music/mixkit-135.mp3`(Mixkit 라이선스, 출처 표기 불필요)를 계속 쓴다.

## 매일 작업 SKILL.md 에 넣을 단락 (초안 — 파일은 오너 확인 후 수정)

> **인스타는 릴스(2026-10-20 오너 결정, 카드뉴스 대신)**: 짝수 날 19:00 인스타 글은 "하루 리뷰 일지 #N" 릴스로 올린다. 만드는 순서와 규칙은 `haru/docs/REEL_RECIPE.md` 를 따른다. 요약: ① `python3 haru/tools/coupang_reviews.py <제휴 링크> --out <폴더>/reviews.json` 으로 실제 리뷰를 읽고 ② 대본 13문장(`script.txt`, 한 줄 = 한 문장, 셋째는 단점)을 쓴 뒤 ③ 힉스필드로 키프레임 3장(soul_2, 9:16, character.json 의 scene_prefix + scene_variants, 제품 없음) → kling3_0 pro 5초 클립 3개(sound off, 8.75크레딧/컷) → 문장별 음성 13건(`generate_audio_batch`, elevenlabs Hallie `10274bf1-fb93-554f-b59f-d620a920fd36`, `lines/NN.mp3`)을 만들고 ④ `reel_lines.py` → `plan.json`(장면·자막·머리말·카드를 문장 번호로 지정, 카드는 리뷰 실제 문장 2 + 하루 메모 1, 단점 구간은 하루 메모만) → `reel_spec.py` → `reels.py` 로 `haru/hub/static/reels/<slug>.mp4` 를 렌더한다. ⑤ `build_hub.py` 후 커밋·PR·머지해 `https://harureviews.date/reels/<slug>.mp4` 가 200 이 되면 큐 아이템에 `video_url` 과 `reel: {spec, series, no}` 를 넣는다. 한 편 크레딧 약 30~35(클립이 26). 클립·음성 생성이 실패하면 그날 인스타는 건너뛰고 보고에 남긴다. 토큰·시크릿은 어디에도 적지 않는다.

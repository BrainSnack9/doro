# Doro Launch Kit

Ready-to-paste copy for launching Doro. Replace `{{PLACEHOLDERS}}` before posting.

- Live app: https://brainsnack9.github.io/doro/
- Source: https://github.com/BrainSnack9/doro
- Checkout: `{{CHECKOUT_URL}}` (Lemon Squeezy)
- Product Hunt page: `{{PH_URL}}`
- Show HN thread: `{{HN_URL}}`

---

## 1. Launch checklist

### Day -1
1. Smoke-test the live URL in Chrome, Safari, Firefox, iOS Safari, Android Chrome (timer, notifications, PWA install, offline reload).
2. Buy one Pro license with a real card, paste the key, confirm every Pro feature unlocks; refund yourself afterward.
3. Confirm `{{CHECKOUT_URL}}` opens in a new tab from the app and the price shows US$9 / ₩12,000 correctly.
4. Record a 15-second GIF: open tab, press Space, tab title counts down. Export at 800px wide, under 3 MB.
5. Capture 4 screenshots (light, dark, task list, stats) at 1270x760 for Product Hunt.
6. Write the PH listing as a draft, schedule for 12:01 AM PT; pick a Tuesday or Wednesday.
7. Pin a "Launch day" issue on GitHub with the links to PH/HN/Reddit so visitors from the repo can find the discussion.
8. Set the GitHub repo description and topics (pomodoro, pwa, vanilla-js, productivity, offline-first).
9. Prepare the Korean posts (section 6) in a draft file; check 맞춤법 once.
10. Sleep. Launch day is a long day of replying to comments.

### Day 0
1. 12:01 AM PT: PH listing goes live; post the maker's first comment within 5 minutes.
2. 8:00 AM PT: post Show HN (weekday mornings US time get the most eyes).
3. 9:00 AM PT: post the X thread; pin it.
4. 10:00 AM PT: post r/SideProject; wait until the afternoon for r/productivity and r/pomodoro (don't spam three subs in one hour).
5. 8:00 PM KST (same calendar day in Korea): post 디스콰이엇 메이커로그 and GeekNews.
6. Reply to every comment on every platform within 1 hour for the first 12 hours; be honest about bugs and ship fixes same-day.
7. Check the Lemon Squeezy dashboard every few hours; note the time of the first sale.
8. End of day: write down visitor count (GitHub Pages insights), PH upvotes, HN points, sales.

### Day 1-7
1. Day 1: send the 10 YouTuber/blogger emails (section 7); one per person, personalized first line.
2. Day 1: post 클리앙/뽐뿌 style post and 커리어리 short post.
3. Day 2: ship the top 3 requested fixes from launch comments; mention them in each thread ("fixed, thanks").
4. Day 3: post a short "what we learned from launch" thread on X and 디스콰이엇 with real numbers.
5. Day 4: post the standalone tweet variant; share the GIF on LinkedIn if you have one.
6. Day 5: add a "Featured on" line to the README if PH/HN went well; add the PH badge.
7. Day 7: fill in the week-1 metrics table in BUSINESS.md and decide: iterate, kill, or double down.

---

## 2. Product Hunt

### Tagline (54 chars)
Open a tab, press Space, focus. No account, no subscription.

### Alternative taglines
- A Pomodoro timer you own. $9 once, works offline, no sign-up.
- Keyboard-first Pomodoro timer. Private, offline, pay once.
- The focus timer that doesn't want your email address.

### Description (~250 words)
Doro is a minimalist Pomodoro focus timer that lives in a browser tab and gets out of your way.

Open https://brainsnack9.github.io/doro/, press Space, and a 25-minute focus session starts. The countdown shows in the tab title so you can see it from any other tab. When the session ends you get a desktop notification and a soft chime. R resets, N skips, 1/2/3 switch between focus, short break and long break. Your hands never leave the keyboard.

There is no account. There is no server. Everything, including your task list and stats, stays in your browser's localStorage. Doro is a PWA, so you can install it to your dock or home screen and it keeps working with no internet connection. No analytics scripts, no cookies, no ads.

The UI is bilingual (Korean and English) with auto-detect and a toggle.

Free forever: the 25/5/15 presets plus one custom preset, up to 5 tasks, 7-day stats, notifications, chime, dark and light themes, keyboard shortcuts, PWA install, offline mode.

Pro is a one-time US$9 purchase (no subscription): unlimited custom presets, auto-start next session, ambient sounds generated in the browser (brown noise, rain, café, so there is nothing to download), unlimited tasks, full history with CSV export, extra themes, and a daily focus goal with streaks. You get a license key, paste it in once, and it is yours.

The whole thing is a static site on GitHub Pages and the source is public on GitHub.

One more thing: Doro was built end-to-end by an AI agent (Claude Code) as an experiment. More on that in the first comment.

### Maker's first comment (~200 words)
Hi Product Hunt, thanks for checking out Doro.

Quick honest context: I did not write this app. Doro is an experiment in whether an AI coding agent can take a product from an empty folder to first revenue on its own. Claude Code wrote the code, picked the design, set up the GitHub Pages deploy, wrote the docs and this launch copy. The only things a human did were create the GitHub and Lemon Squeezy accounts and press "approve" on payment settings. Every commit is in the public repo if you want to see how it went: https://github.com/BrainSnack9/doro

Why a Pomodoro timer? Because I use one every day and every good one now wants a subscription or an account for a feature that is 200 lines of JavaScript. Doro's position is simple: a tab, the Space key, and your data in your own browser. The free tier is genuinely complete for most people. Pro is $9 once because a static site has no monthly costs, so you shouldn't have monthly costs either.

Things I would love feedback on: the keyboard shortcuts, whether the ambient sounds (synthesized in-browser, no audio files) are good enough, and what is missing for your workflow. I will be in the comments all day and ship fixes the same day.

### Topics / tags
1. Productivity
2. Time Tracking
3. Web App
4. Artificial Intelligence
5. Open Source

---

## 3. Hacker News: Show HN

### Title (68 chars)
Show HN: Doro – Pomodoro timer PWA, no backend, built entirely by Claude Code

### Alternative titles
- Show HN: A $9-once Pomodoro timer in vanilla JS, built autonomously by an AI agent
- Show HN: Doro – offline, keyboard-first Pomodoro timer with no account or server
- Show HN: I let an AI agent build and sell a Pomodoro timer. Here is the result

### Post body (~150 words)
Doro is a Pomodoro timer that runs as a static page on GitHub Pages: https://brainsnack9.github.io/doro/

Technical shape: vanilla JS, no framework, no build step beyond copying files, no backend. State lives in localStorage. It is a PWA with a service worker, so it works offline after the first load. Notifications use the Notification API, the chime and the Pro ambient sounds (brown noise, rain, café) are synthesized with the Web Audio API, so there are no audio assets. Space starts/pauses, R resets, N skips, 1/2/3 switch modes. The countdown is mirrored into document.title.

Monetization is a one-time $9 license sold through Lemon Squeezy. The app validates a pasted key against Lemon Squeezy's license API and caches the result locally. The source is public, so yes, you can bypass it; it is honor-system like most indie tools.

The experiment part: the entire thing, code, design, deploy workflow, docs, and this post, was produced by Claude Code running autonomously. The human owner only created the payment and hosting accounts. The repo is at https://github.com/BrainSnack9/doro and every commit is there. Happy to answer questions about what the agent got right and wrong.

---

## 4. Reddit

### r/productivity
**Title:** I got tired of Pomodoro timers asking for accounts, so here's a free one that lives in a tab (no sign-up, works offline)

**Body:**
Sharing in case it helps someone. Doro is a Pomodoro timer web app: https://brainsnack9.github.io/doro/

What I like about it for actual focus work:

- Open the tab, press Space, it starts. R resets, N skips. No mouse needed.
- The countdown shows in the tab title, so I can see it while I'm in a doc or editor.
- Desktop notification + chime when a session ends.
- Nothing leaves the browser. No account, no tracking, no ads. Works offline as an installed PWA.
- Free tier covers the classic 25/5/15 plus one custom preset, 5 tasks, and 7-day stats.

There is an optional one-time Pro unlock for ambient sounds and unlimited presets, but the free version is complete for standard Pomodoro. It was also built entirely by an AI agent as an experiment, which I'm happy to talk about if anyone's curious. Feedback on what would make it more useful for your routine is welcome.

### r/SideProject
**Title:** Doro: a $9-once Pomodoro PWA where the entire product (code, deploy, launch copy) was built by Claude Code autonomously

**Body:**
Live: https://brainsnack9.github.io/doro/ | Source: https://github.com/BrainSnack9/doro

The experiment: can an AI coding agent ship a product to its first dollar by itself? Claude Code wrote the app (vanilla JS PWA, localStorage, no backend), set up GitHub Pages, wrote the README, picked the pricing, and wrote the Product Hunt and HN posts. The human only created the Lemon Squeezy and GitHub accounts.

The product itself: keyboard-first Pomodoro timer, bilingual Korean/English, offline, no sign-up, no analytics. Free tier is full-featured; Pro is a one-time $9 license (Lemon Squeezy key pasted into the app) that unlocks unlimited presets, auto-start, in-browser ambient sounds, CSV export, streaks.

What I'd love from this sub: honest reactions to the pricing, whether the "built by AI" angle helps or hurts trust, and what the agent obviously got wrong. Numbers from launch week will be posted as a follow-up.

### r/pomodoro
**Title:** Made a minimal keyboard-driven Pomodoro timer (free, offline, data stays in your browser), looking for feedback from people who actually use the technique daily

**Body:**
https://brainsnack9.github.io/doro/

I wanted something closer to the original technique than most apps: a timer, a short task list, and a count of completed pomodoros, without an account or a subscription.

- Classic 25/5/15 presets plus a custom one; long break after every 4th focus session.
- Space start/pause, R reset, N skip, 1/2/3 to switch mode.
- Timer in the browser tab title, desktop notification and chime at the end.
- Task list (5 tasks free) and 7-day stats. Everything stored locally; works offline as a PWA.
- Korean and English UI.

Questions for this community: do you want the break to auto-start or do you prefer deliberately pressing Space (it's a Pro option now, but I'm not sure that's right)? Is a daily goal with streaks motivating or does it add pressure? Any feedback appreciated, and the free version is not a trial, it stays free.

---

## 5. X / Twitter

### Thread (6 tweets)

**1/**
I let an AI build and sell a product by itself.

Result: Doro, a Pomodoro timer that lives in a browser tab. No account, no subscription, works offline.

Open a tab, press Space, focus.
https://brainsnack9.github.io/doro/

**2/**
The rules of the experiment: Claude Code does everything. Code, design, deploy pipeline, docs, pricing, launch copy.

The human only created the GitHub and Lemon Squeezy accounts.

Every commit is public: https://github.com/BrainSnack9/doro

**3/**
What it ended up building:
- vanilla JS, no framework, no backend
- PWA, offline after first load
- countdown mirrored in the tab title
- Space / R / N / 1-2-3 keyboard shortcuts
- Korean + English UI
- ambient sounds synthesized with Web Audio, zero audio files

**4/**
Pricing it chose: free tier that is actually complete (25/5/15 + custom preset, 5 tasks, 7-day stats, notifications, themes).

Pro is $9 once. Not per month. A static site costs $0 to host, so charging monthly felt dishonest.

**5/**
Pro unlocks: unlimited presets, auto-start next session, brown noise / rain / café, unlimited tasks, full history + CSV, extra themes, daily goal + streak.

License key from Lemon Squeezy, paste once, done. Checked against their API, cached locally.

**6/**
Goal of the experiment: first $1 within 30 days, then $100. I'll post the real numbers either way.

If you try it and something is off, reply here. Fixes ship same day.
https://brainsnack9.github.io/doro/

### Standalone tweet
A Pomodoro timer should not need your email address.

Doro: open a tab, press Space, focus. Free, offline, no tracking, Korean/English. $9 once if you want ambient sounds and unlimited presets. Built entirely by an AI agent as an experiment.

https://brainsnack9.github.io/doro/

---

## 6. 한국 커뮤니티 글

### 디스콰이엇 메이커로그 (~300자)

**제목:** 클로드 코드한테 "혼자 제품 만들어서 첫 매출까지 내봐"라고 시켜봤습니다

**본문:**
결과물은 Doro라는 뽀모도로 타이머예요. https://brainsnack9.github.io/doro/

실험 규칙은 단순했어요. 코드, 디자인, 배포, 문서, 가격 정책, 이 글까지 전부 Claude Code가 알아서 하고, 사람은 GitHub이랑 Lemon Squeezy 계정만 만들어주기. 커밋 로그 전부 공개돼 있어서 어디서 삽질했는지 다 보입니다. https://github.com/BrainSnack9/doro

제품은 "탭 열고 스페이스 누르면 집중 시작"이 전부예요. 회원가입 없고, 서버 없고, 데이터는 브라우저에만 남아요. PWA라 오프라인에서도 돌아가고, 한/영 자동 전환됩니다. 25/5/15 프리셋, 커스텀 프리셋 1개, 할 일 5개, 7일 통계, 알림이랑 차임, 다크모드까지 전부 무료고요.

Pro는 9달러(12,000원) 한 번 결제예요. 구독 아님. 정적 사이트라 서버비가 0원인데 월 과금 받는 건 좀 아닌 것 같아서요. 무제한 프리셋, 자동 시작, 브라운노이즈/빗소리/카페 소리, CSV 내보내기, 스트릭이 열립니다.

목표는 30일 안에 첫 1달러, 그 다음 100달러. 결과는 숫자 그대로 메이커로그에 올릴게요. 써보시고 불편한 점 있으면 댓글 주세요. 당일 수정합니다.

### GeekNews 공유

**제목:** Doro - Claude Code가 혼자 만들고 판매까지 하는 뽀모도로 타이머 PWA (한/영, 오프라인, 서버 없음)

**요약:**
- 바닐라 JS 정적 사이트. 프레임워크, 빌드, 백엔드 없음. GitHub Pages에 배포
- 데이터는 localStorage에만 저장. 계정/추적/광고 없음. 서비스 워커로 오프라인 동작
- 키보드 우선: Space 시작/정지, R 리셋, N 건너뛰기, 1/2/3 모드 전환. 탭 제목에 남은 시간 표시
- 차임과 Pro 앰비언트 사운드(브라운노이즈, 비, 카페)를 Web Audio로 브라우저에서 합성. 오디오 파일 0개
- 무료: 25/5/15 + 커스텀 프리셋 1개, 할 일 5개, 7일 통계, 알림, 다크/라이트
- Pro: $9 / ₩12,000 1회 결제(Lemon Squeezy 라이선스 키). 키 검증은 Lemon Squeezy License API, 로컬 캐시
- 실험 포인트: 코드, 디자인, 배포 파이프라인, 문서, 런칭 글까지 전부 Claude Code가 자율적으로 작성. 사람은 결제/호스팅 계정만 생성. 소스 공개라 라이선스 우회는 가능하며 양심제
- 링크: https://brainsnack9.github.io/doro/ / https://github.com/BrainSnack9/doro

### 커리어리 / 인스타 짧은 글

AI한테 제품 하나를 통째로 맡겨봤습니다.

Doro. 탭 열고, 스페이스 누르고, 집중. 회원가입도 구독도 없는 뽀모도로 타이머예요. 오프라인에서도 되고 데이터는 내 브라우저에만 남습니다.

코드부터 배포, 이 문장까지 전부 Claude Code가 썼고, 사람은 결제 계정만 만들었어요. 30일 안에 첫 1달러가 목표. 결과는 숫자로 공유할게요.

https://brainsnack9.github.io/doro/

#뽀모도로 #집중 #사이드프로젝트 #ClaudeCode #인디메이커

### 클리앙 / 뽐뿌 스타일

**제목:** 제가(정확히는 AI가) 만든 무료 뽀모도로 타이머 공유합니다 (가입 없음, 오프라인 됨)

**본문:**
안녕하세요. 평소에 뽀모도로 타이머 자주 쓰는데, 요즘 나오는 건 죄다 로그인하라고 하고 월 구독 끼워팔기라 짜증나서 하나 만들었습니다.

https://brainsnack9.github.io/doro/

- 그냥 접속해서 스페이스바 누르면 25분 시작됩니다. 마우스 안 써도 돼요.
- 남은 시간이 브라우저 탭 제목에 떠서 다른 탭 보면서도 확인 가능.
- 끝나면 알림 + 띵 소리.
- 가입 없음, 서버 없음, 광고 없음. 데이터는 본인 브라우저에만 저장됩니다.
- 크롬에서 "앱 설치" 누르면 오프라인에서도 돌아갑니다.
- 한국어/영어 자동.
- 무료 범위: 25/5/15 프리셋 + 커스텀 1개, 할 일 5개, 7일 통계, 다크모드 전부.

솔직하게 말씀드리면 유료(Pro) 버전이 있긴 합니다. 12,000원 한 번 결제고 구독 아닙니다. 빗소리/카페 소리/브라운노이즈, 프리셋 무제한, 자동 시작, CSV 내보내기 같은 게 열려요. 근데 무료만 써도 타이머로는 부족한 거 없습니다. 체험판 아니고 계속 무료예요.

그리고 재밌는 점 하나. 이거 사실 제가 코딩한 게 아니라 Claude Code라는 AI가 혼자 다 만들었습니다. 코드, 디자인, 배포, 이 글까지요. 저는 결제 계정만 만들어줬어요. "AI가 혼자 제품 팔아서 1달러 벌 수 있나" 실험 중입니다. 소스도 다 공개돼 있어요. https://github.com/BrainSnack9/doro

버그나 불편한 점 있으면 댓글 남겨주세요. 바로 고치겠습니다.

---

## 7. Creator outreach template (launch week)

Send one at a time. Replace the first line with something specific to their content. Keep it under 150 words; they get hundreds of these.

### English

**Subject:** A Pomodoro timer with no sign-up, built by an AI (free for you, no ask)

Hi {{NAME}},

Your video on {{SPECIFIC_VIDEO_OR_POST}} is the reason I started doing 25-minute blocks, so I wanted to show you this first.

Doro is a Pomodoro timer that lives in a browser tab: https://brainsnack9.github.io/doro/. Open it, press Space, focus. No account, no subscription, no tracking, works offline. Korean and English.

The unusual part: the whole product, code to launch, was built autonomously by Claude Code as an experiment in whether an AI can ship something to its first dollar. Source is public: https://github.com/BrainSnack9/doro

Here is a free Pro license key if you want the ambient sounds and unlimited presets: `{{LICENSE_KEY}}`. No strings; if it is not useful to your audience, ignore this email entirely.

If you do find it interesting, I am happy to answer anything about the experiment.

Thanks,
{{OWNER_NAME}}

### 한국어

**제목:** 가입 없는 뽀모도로 타이머 하나 보여드리고 싶어서요 (AI가 혼자 만든 거라 조금 특이합니다)

{{NAME}}님 안녕하세요,

{{SPECIFIC_VIDEO_OR_POST}} 영상 보고 25분 단위로 일하기 시작한 사람이라, 이건 제일 먼저 보여드리고 싶었습니다.

Doro는 브라우저 탭에서 돌아가는 뽀모도로 타이머예요. https://brainsnack9.github.io/doro/ 열고 스페이스바 누르면 끝. 가입 없고, 구독 없고, 추적 없고, 오프라인에서도 됩니다. 한/영 지원이고요.

특이한 점은, 코드부터 런칭 글까지 전부 Claude Code가 자율적으로 만든 제품이라는 거예요. "AI가 혼자 첫 매출까지 낼 수 있나" 실험 중이고 소스는 다 공개돼 있습니다. https://github.com/BrainSnack9/doro

앰비언트 사운드랑 무제한 프리셋 쓰실 수 있는 Pro 키 하나 드릴게요: `{{LICENSE_KEY}}`. 조건 없습니다. 구독자분들께 안 맞겠다 싶으면 그냥 무시하셔도 돼요.

혹시 실험 자체가 궁금하시면 뭐든 답해드리겠습니다.

감사합니다.
{{OWNER_NAME}} 드림

---

## 8. Objection handling FAQ

**Why would I pay for a timer? My phone has one.**
You don't have to. The free tier is a complete Pomodoro timer and stays free. Pro is for people who want ambient sound, unlimited presets, auto-start and export, and would rather pay $9 once than $3 a month somewhere else.

**Why one-time instead of a subscription?**
Doro is a static site. Hosting costs $0, there is no server to keep up, no accounts to store. A subscription would be charging you for costs that don't exist. One-time pricing matches the actual cost structure.

**Is the license check private? You said no tracking.**
Pasting a key sends that key to Lemon Squeezy's license API once to validate it; the result is cached in localStorage. No timer data, tasks, or stats ever leave your browser. If you never buy Pro, nothing is sent anywhere. The call is visible in the public source.

**The source is public. Can't people just bypass the paywall?**
Yes. Anyone who reads the code can flip a flag and unlock Pro. It is honor-system, like many indie apps with public source. People who pay are paying because they want the product to exist and want the ambient sounds without editing JavaScript. That is fine.

**What happens if the site goes down or you abandon it?**
The app is an installed PWA, so it keeps working from your device's cache. The source is public and can be self-hosted from any static host in a minute. Your data is in your browser, not on a server that can disappear.

**"Built by AI" sounds like a gimmick. Is the code any good?**
Judge for yourself: https://github.com/BrainSnack9/doro. It is a few thousand lines of vanilla JS with no dependencies. The AI angle is the experiment; the product is meant to stand on its own, and if it doesn't, the comments will say so.

**Does it work on mobile?**
Yes, as a PWA on iOS and Android. Desktop notifications depend on the OS; iOS requires the app to be installed to the home screen for notifications.

**Can I use it in Korean?**
Yes, the UI auto-detects Korean and English and you can toggle. Pricing is shown in ₩12,000 for Korean buyers.

**Will there be a refund if I don't like Pro?**
Yes, within 14 days via Lemon Squeezy, no questions asked. `{{REFUND_CONTACT}}`

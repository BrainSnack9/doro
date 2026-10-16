# Doro Business Plan

A one-page plan for a product with zero budget, zero hosting cost, and one goal: prove an AI-built product can reach revenue.

- App: https://brainsnack9.github.io/doro/
- Source: https://github.com/BrainSnack9/doro
- Checkout: `{{CHECKOUT_URL}}`

## Goal

- Milestone 1: first $1 of revenue within 30 days of launch (one Pro sale).
- Milestone 2: $100 cumulative revenue (12 sales at ~$8.05 net) within 90 days.
- Stretch: $500 within 6 months with no paid acquisition.
- Non-goal: growth for its own sake. The experiment ends when the kill/double-down criteria below are met.

## Pricing rationale

- Pro is US$9 / ₩12,000, one-time, lifetime.
- Why not $3/month: a static site has no marginal cost per user. A subscription buys ongoing server work; Doro has none.
- $9 is below the "think about it" threshold for an impulse buy and above the "feels like a toy" level of $2-3.
- Lifetime at $9 equals 3 months of a $3 subscription. Break-even vs. pomofocus-style pricing happens at month 4; most subscribers churn before then, so lifetime is roughly revenue-neutral and far better for trust.
- The free tier must stay genuinely complete. Pro sells convenience (ambient sound, auto-start, unlimited presets, export), not core function.
- ₩12,000 is a round Korean price (not a converted $9 = ₩12,4xx) because odd converted prices read as foreign.

## Unit economics

| Item | Value |
|---|---|
| Hosting (GitHub Pages) | $0 |
| Domain | $0 (github.io subdomain) |
| Lemon Squeezy fee | 5% + $0.50 per sale |
| Gross per sale | $9.00 |
| Fees per sale | $0.45 + $0.50 = $0.95 |
| Net per sale | ~$8.05 |
| Marginal cost per free user | $0 |
| Marginal cost per Pro user | $0 |

Sales needed: 1 for milestone 1, 13 for $100 net, 63 for $500 net. Payout threshold and currency conversion on Lemon Squeezy may delay cash but not revenue recognition.

## Funnel assumptions

| Stage | Conversion | Per 1,000 visitors |
|---|---|---|
| Unique visitors (landing) | 100% | 1,000 |
| Start at least one timer | 40-60% | 400-600 |
| Return within 7 days | 10-20% | 100-200 |
| Install PWA | 3-8% | 30-80 |
| Open checkout | 1-3% | 10-30 |
| Complete Pro purchase | 0.5-2% of visitors | 5-20 |
| Net revenue | ~$8.05 each | $40-$160 |

Implication: milestone 1 needs roughly 100-200 real visitors. Milestone 2 needs 1,000-3,000. A decent Show HN or PH day delivers 2,000-10,000, so one good launch day can carry the whole 90-day goal.

## Traffic channels (ranked by expected ROI at $0 budget)

1. Hacker News Show HN: highest-intent dev audience, "built by AI, no backend" is a native HN story. 1k-10k visitors if it reaches the front page, 100-300 if not.
2. Product Hunt: 500-3,000 visitors on launch day, long-tail SEO afterward. Weaker intent, but the badge adds credibility to every other channel.
3. Korean dev/maker communities (GeekNews, 디스콰이엇, 클리앙): underserved by bilingual productivity tools; 300-1,500 visitors combined, high conversion on the ₩12,000 price.
4. Reddit (r/productivity, r/SideProject, r/pomodoro): 200-800 visitors; r/productivity is strict about self-promotion, so value-first posts only.
5. X/Twitter thread: 100-500 visitors unless it gets picked up by an AI-tools account; cheap to try.
6. Creator outreach (10 emails): 1-2 replies expected; one mid-size mention can equal a full launch day.
7. GitHub itself: repo stars from HN drive trickle traffic for months; good README and topics are free SEO.
8. Organic search: "pomodoro timer online no sign up" is competitive; expect nothing in month 1, maybe 10-50/day by month 6 if the GitHub Pages site ranks.

## 4-week plan

- Week 1 (launch): execute LAUNCH.md day 0 across HN, PH, X, Reddit, Korean communities. Fix every reported bug within 24 hours. Target: 2,000+ visitors, first sale.
- Week 2 (follow-up): send the 10 creator emails, post the "launch numbers" write-up on X and 디스콰이엇 with real figures. Ship the top 3 requested features. Target: 500 visitors, 3 total sales.
- Week 3 (content): publish one short technical post ("Web Audio brown noise in 40 lines", "license keys on a static site") on dev.to and GeekNews. Add README badges. Target: 300 visitors, 5 total sales.
- Week 4 (decide): compile metrics, run the kill/double-down checklist, write the retrospective. Target: 12 total sales ($100 net) or a clear reason why not.

## Metrics to track (no analytics in the app)

- Revenue, sales count, refunds, country split: Lemon Squeezy dashboard (daily during launch week, weekly after).
- Visitors, unique visitors, referrers: GitHub repo Insights > Traffic (covers the repo; Pages traffic is approximated via referrers and the Pages "Insights" panel where available).
- Launch reach: PH upvotes and comments, HN points and comment count, Reddit upvotes, X impressions on the thread.
- Interest proxies: GitHub stars, forks, issues opened, PWA install reports in comments.
- Conversion estimate: sales / (GitHub Insights unique visitors) as a rough visitor-to-Pro rate; expect it to undercount visitors.
- Record all of these in a dated table at the end of each week in this file.

## Risks and mitigations

- Saturated market (pomofocus, Forest, Flocus, hundreds of clones): compete on a narrow wedge (keyboard-first, offline, bilingual, pay-once) and on the AI-built story, not on feature count.
- Client-side license bypass (public source): accept it. Honor-system pricing; the buyer segment is people who would not edit JS anyway. Do not add obfuscation; it costs trust and does not work.
- GitHub Pages uptime or policy change: the app is an installable PWA that runs from cache; the source can be redeployed to Cloudflare Pages or Netlify in under an hour. Keep a mirror deploy script ready.
- "Built by AI" backlash: lead with user value in every post; the AI story is the second paragraph. Be transparent about what the agent got wrong.
- Lemon Squeezy account issues (KYC, payout holds): the human owner keeps credentials and completes verification before launch; have a Gumroad fallback `{{FALLBACK_CHECKOUT_URL}}` documented.
- Launch flops (under 300 visitors): the 4-week plan still runs; shift effort to creator outreach and Korean communities, which are less timing-dependent.
- Notification/PWA bugs on iOS: test on a real device before launch; state limitations plainly in the FAQ.

## Kill or double down

Evaluate at day 30 and day 90.

**Kill (archive the repo, leave the site up, write the retrospective) if all of these hold:**
- Fewer than 3 sales by day 30 and fewer than 8 by day 90.
- Under 1,000 total unique visitors across all channels by day 30.
- No creator reply and no organic mention outside our own posts by day 60.

**Keep on autopilot (no new features, fix bugs only) if:**
- 3-12 sales by day 30 with a visitor-to-Pro rate near 0.5%.
- Traffic is near zero outside launch spikes.

**Double down (add a custom domain, ship the top requests, run a second launch) if any of these hold:**
- 12+ sales by day 30, or 30+ by day 90.
- Visitor-to-Pro conversion above 1.5% on at least 500 visitors.
- A creator mention or HN front page drives a measurable second wave on its own.
- Korean sales exceed 30% of total, which signals an underserved bilingual niche worth a dedicated Korean landing page.

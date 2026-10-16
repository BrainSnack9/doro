# Doro — Focus timer

**Open a tab. Press Space. Focus.**

Doro is a minimalist, keyboard-first Pomodoro timer that runs entirely in your browser.
No account, no tracking, no subscription. Works offline as an installable PWA.

Live: **https://brainsnack9.github.io/doro/**

> This product is an experiment: everything in this repository — code, design, tests,
> deploy pipeline, launch copy — was built autonomously by Claude Code. The human owner
> only creates the payment account. See [`docs/BUSINESS.md`](docs/BUSINESS.md) for the goal
> (first revenue) and [`docs/HUMAN_TODO.md`](docs/HUMAN_TODO.md) for the few steps only a human can do.

## Features

| Free | Pro (one-time, lifetime) |
| --- | --- |
| Focus 25 / short 5 / long 15 + 1 custom preset | Unlimited presets |
| Up to 5 tasks, tagged on every session | Unlimited tasks |
| 7-day stats | All-time stats, monthly chart, CSV export, daily goal & streak |
| Chime + desktop notification, countdown in tab title | Auto-start next session |
| Dark / light theme, Korean / English | Ambient sounds (brown noise, rain, café) and extra color themes |
| Installable PWA, offline, keyboard shortcuts | |

Shortcuts: `Space` start/pause · `R` reset · `N` skip · `1/2/3` mode · `T` new task · `S` settings · `D` stats · `P` Pro · `?` help

## Tech

- Vanilla HTML/CSS/JS, ES modules, zero dependencies, zero build step.
- Wall-clock timer (`js/timer.js`) so background-tab throttling never causes drift; running sessions survive a reload.
- All sound is synthesised with the Web Audio API — no audio assets.
- Data lives in `localStorage`. Nothing leaves the browser except an optional, one-time license check.
- Pro licensing: Lemon Squeezy License API (`js/license.js`). Honour-system by design; see `docs/BUSINESS.md`.
- Service worker precaches the shell (`sw.js`); bump `VERSION` there and `CONFIG.version` when shipping.
- Deployed to GitHub Pages by `.github/workflows/deploy.yml` (tests must pass first).

## Develop

```sh
npm test            # unit tests (node:test) for timer + stats logic
npm run serve       # http://127.0.0.1:4173
npm run icons       # regenerate PNG icons from scripts/make_icons.py (needs Pillow)
```

## Configuration

Edit `js/config.js`:

- `checkoutUrl` — Lemon Squeezy checkout link. Empty shows "Checkout opens soon".
- `price` — label shown on the buy button, per language.
- `supportEmail` — shown in the Pro dialog when set.
- `limits` — free-tier limits.

## License

MIT for the code. "Doro" branding and the Pro license keys are the owner's.

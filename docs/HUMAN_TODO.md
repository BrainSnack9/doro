# What only a human can do (≈ 30 minutes total)

Everything else is already done and deployed. These steps need a real identity, bank account, or account login that an AI cannot (and should not) create.

## 1. Confirm the site is live (2 min)

- Open https://brainsnack9.github.io/doro/ . If it 404s, open the repo → **Settings → Pages** and set **Source: GitHub Actions**, then re-run the latest workflow under **Actions**.
- Optional: point a custom domain at it (Settings → Pages → Custom domain). `doro.app`-style names are usually taken; `getdoro.com`, `doro.so`, `usedoro.com` are worth checking.

## 2. Create the store (15 min) — Lemon Squeezy

1. Sign up at https://app.lemonsqueezy.com (acts as merchant of record, handles VAT/tax globally, pays out to Korean bank accounts via Payoneer/PayPal/bank).
2. **Products → New product**: name `Doro Pro (lifetime)`, price **$9 USD**, one-time payment.
3. In the product, enable **License keys** (Settings → "Generate license keys"), activation limit **3** (3 browsers/devices per purchase).
4. Copy the **Checkout link** (`https://<store>.lemonsqueezy.com/buy/<uuid>`).
5. Complete store verification (identity + payout details) so you can leave test mode. Until then checkout runs in test mode — fine for trying the flow with a test card.

## 3. Wire the store into the app (3 min)

In `js/config.js`:

```js
checkoutUrl: 'https://<store>.lemonsqueezy.com/buy/<uuid>',
supportEmail: 'you@example.com',
```

Commit and push — the workflow redeploys automatically. Then:

- Make a test purchase (test mode), copy the license key from the receipt email, open the site → **Pro → Already have a license key?** → paste → **Activate**. The Pro dot turns colored.
- If activation fails with a network error, Lemon Squeezy's license endpoint may be blocking the request origin; tell Claude and it will add a tiny proxy (Cloudflare Worker) — a 10-minute change.

## 4. Launch (owner-only clicks, ~10 min)

All copy is ready in `docs/LAUNCH.md`. Accounts needed: Product Hunt, Hacker News, Reddit, X, 디스콰이엇, GeekNews. Paste, post, done.

## 5. Watch for the first sale

- Lemon Squeezy dashboard → Orders. Each sale nets ≈ $8.05.
- Tell Claude when the first order lands — that is the finish line of the experiment, and the start of the next iteration (see `docs/BUSINESS.md`, "double down" criteria).

## Things Claude will keep doing without you

- Fixing bugs reported in GitHub Issues.
- Shipping the next features (planned: focus-mode fullscreen, Spotify-style session ambience mixer, weekly email-free report page).
- Updating launch copy based on what gets traction.

// Doro runtime configuration.
// Only the owner needs to touch this file: paste the Lemon Squeezy checkout URL
// once the store exists (see docs/HUMAN_TODO.md). Everything else works without it.
export const CONFIG = {
  version: '0.1.0',

  // Lemon Squeezy checkout link for "Doro Pro (lifetime)". Empty = button shows "coming soon".
  checkoutUrl: '',

  // Shown on the Pro button / dialog. Keep in sync with the store price.
  price: { en: '$9 once', ko: '₩12,000 한 번' },

  // Lemon Squeezy License API (public, no API key needed for activate/validate).
  licenseApi: 'https://api.lemonsqueezy.com/v1/licenses',

  // Where users can reach a human (shown in the Pro dialog when set).
  supportEmail: '',

  repoUrl: 'https://github.com/BrainSnack9/doro',

  // Free tier limits. Pro removes all of them.
  limits: {
    freeTasks: 5,
    freeHistoryDays: 7,
    freeCustomPresets: 1,
  },
};

// Tiny localStorage wrapper. Everything Doro knows lives in the user's browser.
const PREFIX = 'doro:';

export function load(key, fallback = null) {
  try {
    const raw = localStorage.getItem(PREFIX + key);
    return raw == null ? fallback : JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export function save(key, value) {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

export function remove(key) {
  try { localStorage.removeItem(PREFIX + key); } catch { /* ignore */ }
}

export const DEFAULT_SETTINGS = Object.freeze({
  durations: { focus: 25, short: 5, long: 15 },
  longBreakEvery: 4,
  autoStartBreaks: false, // Pro
  autoStartFocus: false, // Pro
  sound: 'chime', // chime | bell | digital | none
  volume: 0.6,
  notifications: true,
  theme: 'auto', // auto | light | dark
  accent: 'classic', // classic | forest | mono | sunset (last three Pro)
  lang: 'auto', // auto | en | ko
  dailyGoal: 8, // Pro
  ambient: 'off', // off | brown | rain | cafe (Pro)
  ambientVolume: 0.4,
  titleCountdown: true,
  presets: [], // [{ name, focus, short, long }]
});

export function loadSettings() {
  const s = load('settings', {});
  return {
    ...DEFAULT_SETTINGS,
    ...s,
    durations: { ...DEFAULT_SETTINGS.durations, ...(s.durations || {}) },
    presets: Array.isArray(s.presets) ? s.presets : [],
  };
}

export function saveSettings(settings) {
  save('settings', settings);
}

export function uid() {
  return Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
}

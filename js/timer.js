// Pure timer state machine. No DOM, no storage — fully unit-testable.
// Time is wall-clock based (endAt), so background-tab throttling never causes drift.

export const MODES = ['focus', 'short', 'long'];

export const DEFAULT_DURATIONS = { focus: 25, short: 5, long: 15 };

export class Timer {
  constructor({ durations = DEFAULT_DURATIONS, longBreakEvery = 4, now = () => Date.now() } = {}) {
    this.now = now;
    this.durations = { ...DEFAULT_DURATIONS, ...durations }; // minutes
    this.longBreakEvery = Math.max(1, longBreakEvery | 0);
    this.mode = 'focus';
    this.running = false;
    this.endAt = null;
    this.remaining = this.durationMs('focus');
    this.focusCount = 0; // completed (or skipped) focus sessions, drives long-break cadence
    this.startedAt = null; // when the current session first started (for history)
    this.listeners = new Set();
  }

  durationMs(mode = this.mode) {
    return Math.round((this.durations[mode] || 0) * 60 * 1000);
  }

  subscribe(fn) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  emit(type, payload = {}) {
    for (const fn of [...this.listeners]) fn({ type, ...payload, timer: this });
  }

  setDurations(partial) {
    this.durations = { ...this.durations, ...partial };
    if (!this.running) this.remaining = this.durationMs();
    this.emit('change');
  }

  setLongBreakEvery(n) {
    this.longBreakEvery = Math.max(1, n | 0);
    this.emit('change');
  }

  setMode(mode) {
    if (!MODES.includes(mode)) throw new Error(`unknown mode ${mode}`);
    this.mode = mode;
    this.running = false;
    this.endAt = null;
    this.startedAt = null;
    this.remaining = this.durationMs(mode);
    this.emit('mode');
  }

  start() {
    if (this.running) return;
    if (this.remaining <= 0) this.remaining = this.durationMs();
    const t = this.now();
    this.endAt = t + this.remaining;
    this.running = true;
    if (this.startedAt == null) this.startedAt = t;
    this.emit('start');
  }

  pause() {
    if (!this.running) return;
    this.remaining = Math.max(0, this.endAt - this.now());
    this.running = false;
    this.endAt = null;
    this.emit('pause');
  }

  toggle() {
    if (this.running) this.pause();
    else this.start();
  }

  reset() {
    this.running = false;
    this.endAt = null;
    this.startedAt = null;
    this.remaining = this.durationMs();
    this.emit('reset');
  }

  /** Call on an interval (e.g. every 250ms). Emits 'tick' or 'complete'. */
  tick() {
    if (!this.running) return;
    const rem = this.endAt - this.now();
    if (rem <= 0) {
      this.remaining = 0;
      this.complete();
    } else {
      this.remaining = rem;
      this.emit('tick');
    }
  }

  nextMode(finished = this.mode) {
    if (finished !== 'focus') return 'focus';
    return this.focusCount % this.longBreakEvery === 0 ? 'long' : 'short';
  }

  /** Natural completion of the current session. */
  complete() {
    const finished = this.mode;
    const endedAt = this.now();
    const startedAt = this.startedAt ?? endedAt - this.durationMs(finished);
    this.running = false;
    this.endAt = null;
    if (finished === 'focus') this.focusCount += 1;
    const next = this.nextMode(finished);
    this.startedAt = null;
    this.emit('complete', { finished, next, startedAt, endedAt, minutes: this.durations[finished] });
    this.mode = next;
    this.remaining = this.durationMs(next);
    this.emit('mode');
  }

  /** Skip to the next session without counting it as completed. */
  skip() {
    const skipped = this.mode;
    const endedAt = this.now();
    const elapsedMs = this.running
      ? this.durationMs(skipped) - (this.endAt - endedAt)
      : this.durationMs(skipped) - this.remaining;
    const startedAt = this.startedAt;
    this.running = false;
    this.endAt = null;
    if (skipped === 'focus') this.focusCount += 1;
    const next = this.nextMode(skipped);
    this.startedAt = null;
    this.emit('skip', { skipped, next, startedAt, endedAt, elapsedMs: Math.max(0, elapsedMs) });
    this.mode = next;
    this.remaining = this.durationMs(next);
    this.emit('mode');
  }

  /** 0 → 1 fraction of the current session elapsed. */
  get progress() {
    const total = this.durationMs();
    if (total <= 0) return 1;
    return Math.min(1, Math.max(0, 1 - this.remaining / total));
  }

  /** 1-based index of the current focus session within the long-break cycle. */
  get cyclePosition() {
    return (this.focusCount % this.longBreakEvery) + 1;
  }

  /** Serialisable snapshot so a page reload can resume a running timer. */
  snapshot() {
    return {
      mode: this.mode,
      running: this.running,
      endAt: this.endAt,
      remaining: this.remaining,
      focusCount: this.focusCount,
      startedAt: this.startedAt,
    };
  }

  restore(snap) {
    if (!snap || !MODES.includes(snap.mode)) return;
    this.mode = snap.mode;
    this.focusCount = snap.focusCount | 0;
    this.startedAt = snap.startedAt ?? null;
    if (snap.running && typeof snap.endAt === 'number') {
      const rem = snap.endAt - this.now();
      if (rem > 0) {
        this.running = true;
        this.endAt = snap.endAt;
        this.remaining = rem;
      } else {
        // The session finished while the page was closed: treat it as completed.
        this.running = false;
        this.endAt = null;
        this.remaining = 0;
        this.emit('mode');
        this.complete();
        return;
      }
    } else {
      this.running = false;
      this.endAt = null;
      this.remaining = Math.min(this.durationMs(snap.mode), Math.max(0, snap.remaining ?? this.durationMs(snap.mode)));
    }
    this.emit('mode');
  }
}

/** "25:00", "4:09", "120:00". Rounds up so the display never shows 0:00 while running. */
export function formatTime(ms) {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

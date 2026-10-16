// Pure helpers for session history. A session: { start, end, mode, minutes, task }

const DAY = 24 * 60 * 60 * 1000;

/** Local calendar key YYYY-MM-DD for a timestamp. */
export function dayKey(ts) {
  const d = new Date(ts);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function startOfDay(ts) {
  const d = new Date(ts);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

/** Only focus sessions count towards stats. */
export function focusSessions(sessions) {
  return sessions.filter((s) => s.mode === 'focus');
}

/**
 * Per-day totals for the last `days` days (oldest first).
 * Returns [{ day, ts, minutes, sessions }]
 */
export function dailyTotals(sessions, { days = 7, now = Date.now() } = {}) {
  const buckets = new Map();
  const today = startOfDay(now);
  for (let i = days - 1; i >= 0; i--) {
    const ts = today - i * DAY;
    buckets.set(dayKey(ts), { day: dayKey(ts), ts, minutes: 0, sessions: 0 });
  }
  for (const s of focusSessions(sessions)) {
    const b = buckets.get(dayKey(s.end));
    if (!b) continue;
    b.minutes += s.minutes || 0;
    b.sessions += 1;
  }
  return [...buckets.values()];
}

export function totals(sessions) {
  let minutes = 0;
  let count = 0;
  for (const s of focusSessions(sessions)) {
    minutes += s.minutes || 0;
    count += 1;
  }
  return { minutes, sessions: count };
}

export function todayTotals(sessions, now = Date.now()) {
  const key = dayKey(now);
  return totals(focusSessions(sessions).filter((s) => dayKey(s.end) === key));
}

/**
 * Current streak of consecutive days meeting `goal` focus sessions.
 * Today counts if met; otherwise the streak is measured up to yesterday.
 */
export function streak(sessions, { goal = 1, now = Date.now() } = {}) {
  const perDay = new Map();
  for (const s of focusSessions(sessions)) {
    const k = dayKey(s.end);
    perDay.set(k, (perDay.get(k) || 0) + 1);
  }
  let count = 0;
  let cursor = startOfDay(now);
  if ((perDay.get(dayKey(cursor)) || 0) < goal) cursor -= DAY; // today not (yet) met
  while ((perDay.get(dayKey(cursor)) || 0) >= goal) {
    count += 1;
    cursor -= DAY;
  }
  return count;
}

/** Drop sessions older than `days` days (used to enforce the free history window). */
export function trimHistory(sessions, { days, now = Date.now() }) {
  const cutoff = startOfDay(now) - (days - 1) * DAY;
  return sessions.filter((s) => s.end >= cutoff);
}

function csvCell(v) {
  const s = v == null ? '' : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function toCSV(sessions) {
  const header = ['start', 'end', 'mode', 'minutes', 'task'];
  const rows = sessions.map((s) => [
    new Date(s.start).toISOString(),
    new Date(s.end).toISOString(),
    s.mode,
    s.minutes,
    s.task || '',
  ]);
  return [header, ...rows].map((r) => r.map(csvCell).join(',')).join('\n') + '\n';
}

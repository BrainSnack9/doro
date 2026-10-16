import { test } from 'node:test';
import assert from 'node:assert/strict';
import { dailyTotals, todayTotals, totals, streak, trimHistory, toCSV, dayKey } from '../js/stats.js';

const DAY = 86_400_000;
const NOW = new Date(2026, 9, 16, 14, 0, 0).getTime(); // local 2026-10-16 14:00

function focus(endOffsetDays, minutes = 25, task = '') {
  const end = NOW - endOffsetDays * DAY;
  return { start: end - minutes * 60_000, end, mode: 'focus', minutes, task };
}

test('dayKey uses the local calendar date', () => {
  assert.equal(dayKey(NOW), '2026-10-16');
});

test('dailyTotals returns exactly N buckets, oldest first, ignoring breaks', () => {
  const sessions = [
    focus(0), focus(0), focus(1), focus(6), focus(7),
    { start: NOW - 5 * 60_000, end: NOW, mode: 'short', minutes: 5 },
  ];
  const rows = dailyTotals(sessions, { days: 7, now: NOW });
  assert.equal(rows.length, 7);
  assert.equal(rows[6].day, '2026-10-16');
  assert.equal(rows[6].sessions, 2);
  assert.equal(rows[6].minutes, 50);
  assert.equal(rows[5].sessions, 1);
  assert.equal(rows[0].day, '2026-10-10');
  assert.equal(rows[0].sessions, 1);
  assert.equal(rows.reduce((a, r) => a + r.sessions, 0), 4); // the 7-days-ago one is out of window
});

test('totals and todayTotals', () => {
  const sessions = [focus(0, 25), focus(0, 50), focus(3, 25)];
  assert.deepEqual(totals(sessions), { minutes: 100, sessions: 3 });
  assert.deepEqual(todayTotals(sessions, NOW), { minutes: 75, sessions: 2 });
});

test('streak counts consecutive goal-met days, tolerating an unfinished today', () => {
  // goal 2/day: today 1 (not met), yesterday 2, day-2 3, day-3 0
  const sessions = [focus(0), focus(1), focus(1), focus(2), focus(2), focus(2)];
  assert.equal(streak(sessions, { goal: 2, now: NOW }), 2);
  // once today is met, it joins the streak
  assert.equal(streak([...sessions, focus(0)], { goal: 2, now: NOW }), 3);
  assert.equal(streak([], { goal: 1, now: NOW }), 0);
});

test('trimHistory keeps only the last N calendar days', () => {
  const sessions = [focus(0), focus(6), focus(7), focus(30)];
  const kept = trimHistory(sessions, { days: 7, now: NOW });
  assert.equal(kept.length, 2);
});

test('toCSV escapes commas and quotes', () => {
  const csv = toCSV([focus(0, 25, 'write "report", v2')]);
  const lines = csv.trim().split('\n');
  assert.equal(lines[0], 'start,end,mode,minutes,task');
  assert.ok(lines[1].endsWith(',focus,25,"write ""report"", v2"'));
});

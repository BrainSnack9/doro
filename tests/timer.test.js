import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Timer, formatTime } from '../js/timer.js';

function clock(start = 1_000_000) {
  let t = start;
  const now = () => t;
  now.advance = (ms) => { t += ms; };
  return now;
}

test('formatTime rounds up and pads seconds', () => {
  assert.equal(formatTime(25 * 60 * 1000), '25:00');
  assert.equal(formatTime(249_001), '4:10');
  assert.equal(formatTime(999), '0:01');
  assert.equal(formatTime(0), '0:00');
  assert.equal(formatTime(-5), '0:00');
  assert.equal(formatTime(120 * 60 * 1000), '120:00');
});

test('starts with focus duration and counts down by wall clock', () => {
  const now = clock();
  const t = new Timer({ now });
  assert.equal(t.mode, 'focus');
  assert.equal(t.remaining, 25 * 60_000);
  t.start();
  now.advance(60_000);
  t.tick();
  assert.equal(t.remaining, 24 * 60_000);
  assert.ok(Math.abs(t.progress - 1 / 25) < 1e-9);
});

test('pause freezes remaining; resume continues from there', () => {
  const now = clock();
  const t = new Timer({ now });
  t.start();
  now.advance(5_000);
  t.pause();
  now.advance(60_000); // time passes while paused
  t.tick();
  assert.equal(t.remaining, 25 * 60_000 - 5_000);
  t.start();
  now.advance(5_000);
  t.tick();
  assert.equal(t.remaining, 25 * 60_000 - 10_000);
});

test('completion emits a session record and moves to a short break', () => {
  const now = clock();
  const t = new Timer({ now });
  const events = [];
  t.subscribe((e) => events.push(e));
  t.start();
  now.advance(25 * 60_000);
  t.tick();
  const done = events.find((e) => e.type === 'complete');
  assert.ok(done);
  assert.equal(done.finished, 'focus');
  assert.equal(done.next, 'short');
  assert.equal(done.minutes, 25);
  assert.equal(done.endedAt - done.startedAt, 25 * 60_000);
  assert.equal(t.mode, 'short');
  assert.equal(t.running, false);
  assert.equal(t.remaining, 5 * 60_000);
  assert.equal(t.focusCount, 1);
});

test('every Nth focus is followed by a long break', () => {
  const now = clock();
  const t = new Timer({ now, longBreakEvery: 4 });
  const nexts = [];
  t.subscribe((e) => { if (e.type === 'complete' && e.finished === 'focus') nexts.push(e.next); });
  for (let i = 0; i < 8; i++) {
    t.setMode('focus');
    t.start();
    now.advance(25 * 60_000);
    t.tick();
  }
  assert.deepEqual(nexts, ['short', 'short', 'short', 'long', 'short', 'short', 'short', 'long']);
});

test('cyclePosition reports the 1-based focus index within a cycle', () => {
  const t = new Timer({ longBreakEvery: 4 });
  assert.equal(t.cyclePosition, 1);
  t.focusCount = 3;
  assert.equal(t.cyclePosition, 4);
  t.focusCount = 4;
  assert.equal(t.cyclePosition, 1);
});

test('skip advances without a complete event but reports elapsed time', () => {
  const now = clock();
  const t = new Timer({ now });
  const events = [];
  t.subscribe((e) => events.push(e));
  t.start();
  now.advance(90_000);
  t.skip();
  assert.ok(!events.some((e) => e.type === 'complete'));
  const skip = events.find((e) => e.type === 'skip');
  assert.equal(skip.skipped, 'focus');
  assert.equal(skip.elapsedMs, 90_000);
  assert.equal(t.mode, 'short');
  assert.equal(t.focusCount, 1);
});

test('a skipped break always returns to focus', () => {
  const t = new Timer();
  t.setMode('long');
  t.skip();
  assert.equal(t.mode, 'focus');
  assert.equal(t.focusCount, 0);
});

test('setDurations updates the idle timer immediately but not a running one', () => {
  const now = clock();
  const t = new Timer({ now });
  t.setDurations({ focus: 50 });
  assert.equal(t.remaining, 50 * 60_000);
  t.start();
  now.advance(1000);
  t.tick();
  t.setDurations({ focus: 10 });
  assert.equal(t.remaining, 50 * 60_000 - 1000);
});

test('reset restores the full duration and stops the timer', () => {
  const now = clock();
  const t = new Timer({ now });
  t.start();
  now.advance(10_000);
  t.tick();
  t.reset();
  assert.equal(t.running, false);
  assert.equal(t.remaining, 25 * 60_000);
  assert.equal(t.startedAt, null);
});

test('snapshot/restore resumes a running session across reloads', () => {
  const now = clock();
  const a = new Timer({ now });
  a.start();
  now.advance(60_000);
  a.tick();
  const snap = a.snapshot();

  now.advance(30_000); // "page was closed" for 30s
  const b = new Timer({ now });
  b.restore(snap);
  assert.equal(b.running, true);
  assert.equal(b.remaining, 25 * 60_000 - 90_000);
  assert.equal(b.startedAt, a.startedAt);
});

test('restore completes a session that ended while the page was closed', () => {
  const now = clock();
  const a = new Timer({ now });
  a.start();
  const snap = a.snapshot();
  now.advance(26 * 60_000);
  const b = new Timer({ now });
  const events = [];
  b.subscribe((e) => events.push(e.type));
  b.restore(snap);
  assert.ok(events.includes('complete'));
  assert.equal(b.mode, 'short');
  assert.equal(b.running, false);
  assert.equal(b.focusCount, 1);
});

test('restore of a paused snapshot keeps remaining time', () => {
  const now = clock();
  const a = new Timer({ now });
  a.start();
  now.advance(5_000);
  a.pause();
  const b = new Timer({ now });
  b.restore(a.snapshot());
  assert.equal(b.running, false);
  assert.equal(b.remaining, 25 * 60_000 - 5_000);
});

test('tick is a no-op when idle', () => {
  const t = new Timer();
  const events = [];
  t.subscribe((e) => events.push(e.type));
  t.tick();
  assert.deepEqual(events, []);
});

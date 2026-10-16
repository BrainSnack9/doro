import { CONFIG } from './config.js';
import { Timer, MODES, formatTime } from './timer.js';
import { load, save, remove, loadSettings, saveSettings, uid } from './store.js';
import { t, setLang, detectLang, applyTranslations, getLang } from './i18n.js';
import { playChime, unlockAudio, Ambient } from './audio.js';
import { isPro, activate, revalidate, deactivate, getLicense } from './license.js';
import { dailyTotals, todayTotals, totals, streak, toCSV, dayKey } from './stats.js';

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

// ---------- state ----------
let settings = loadSettings();
let tasks = load('tasks', []);
let sessions = load('sessions', []);
let currentTaskId = load('currentTask', null);

const timer = new Timer({ durations: settings.durations, longBreakEvery: settings.longBreakEvery });
const ambient = new Ambient();

// ---------- elements ----------
const el = {
  time: $('#time'),
  ring: $('#ring-fg'),
  toggle: $('#btn-toggle'),
  toggleLabel: $('#toggle-label'),
  reset: $('#btn-reset'),
  skip: $('#btn-skip'),
  cycle: $('#cycle'),
  currentTask: $('#current-task'),
  modes: $$('.mode'),
  taskForm: $('#task-form'),
  taskInput: $('#task-input'),
  taskList: $('#task-list'),
  taskEmpty: $('#task-empty'),
  taskLimit: $('#task-limit'),
  clearDone: $('#btn-clear-done'),
  todaySessions: $('#today-sessions'),
  todayMinutes: $('#today-minutes'),
  goalText: $('#goal-text'),
  streakText: $('#streak-text'),
  goalCell: $('#goal-cell'),
  streakCell: $('#streak-cell'),
  weekBars: $('#week-bars'),
  toast: $('#toast'),
  proPill: $('#btn-pro'),
  dlgSettings: $('#dlg-settings'),
  dlgStats: $('#dlg-stats'),
  dlgPro: $('#dlg-pro'),
  dlgHelp: $('#dlg-help'),
};

// ---------- helpers ----------
function persistTimer() {
  save('timer', timer.snapshot());
}
function persistTasks() {
  save('tasks', tasks);
  save('currentTask', currentTaskId);
}
function persistSessions() {
  save('sessions', sessions);
}
function pro() {
  return isPro();
}
function modeLabel(mode) {
  return t(`mode.${mode}`);
}
function currentTask() {
  return tasks.find((x) => x.id === currentTaskId && !x.done) || null;
}

let toastTimer = null;
function toast(msg, { action, onAction, sticky } = {}) {
  el.toast.innerHTML = '';
  el.toast.append(document.createTextNode(msg));
  if (action) {
    const b = document.createElement('button');
    b.className = 'link';
    b.type = 'button';
    b.textContent = action;
    b.addEventListener('click', () => { onAction?.(); hideToast(); });
    el.toast.append(b);
  }
  el.toast.hidden = false;
  clearTimeout(toastTimer);
  if (!sticky) toastTimer = setTimeout(hideToast, 3500);
}
function hideToast() {
  el.toast.hidden = true;
}

function openDialog(dlg) {
  if (dlg.open) return;
  dlg.showModal();
}
function anyDialogOpen() {
  return $$('dialog[open]').length > 0;
}

// ---------- theme & language ----------
function applyTheme() {
  const root = document.documentElement;
  if (settings.theme === 'auto') root.removeAttribute('data-theme');
  else root.dataset.theme = settings.theme;
  const accent = pro() ? settings.accent : 'classic';
  if (accent === 'classic') root.removeAttribute('data-accent');
  else root.dataset.accent = accent;
}

function applyLang() {
  setLang(detectLang(settings.lang));
  applyTranslations();
  $('#btn-lang').textContent = getLang() === 'ko' ? 'English' : '한국어';
  renderAll();
}

// ---------- rendering ----------
function renderTimer() {
  const text = formatTime(timer.remaining);
  el.time.textContent = text;
  el.ring.style.strokeDashoffset = String(1 - timer.progress);
  document.body.dataset.mode = timer.mode;
  el.modes.forEach((b) => b.setAttribute('aria-selected', String(b.dataset.mode === timer.mode)));

  const full = timer.remaining >= timer.durationMs();
  el.toggleLabel.textContent = timer.running ? t('btn.pause') : full ? t('btn.start') : t('btn.resume');
  el.toggle.classList.toggle('is-running', timer.running);

  const next = timer.nextMode();
  const total = timer.longBreakEvery;
  el.cycle.textContent = timer.mode === 'focus'
    ? `${t('cycle.session', { n: timer.cyclePosition, total })} · ${t('cycle.next', { mode: modeLabel(next) })}`
    : t('cycle.next', { mode: modeLabel('focus') });

  const task = currentTask();
  el.currentTask.hidden = !(task && timer.mode === 'focus');
  if (task) el.currentTask.textContent = task.title;

  if (settings.titleCountdown && (timer.running || !full)) {
    document.title = `${text} · ${modeLabel(timer.mode)} — Doro`;
  } else {
    document.title = 'Doro — Focus timer';
  }
}

function renderTasks() {
  el.taskList.innerHTML = '';
  const frag = document.createDocumentFragment();
  for (const task of tasks) {
    const li = document.createElement('li');
    li.className = 'task' + (task.id === currentTaskId ? ' is-current' : '') + (task.done ? ' is-done' : '');
    li.dataset.id = task.id;

    const check = document.createElement('input');
    check.type = 'checkbox';
    check.className = 'task-check';
    check.checked = !!task.done;
    check.setAttribute('aria-label', task.title);
    check.addEventListener('change', () => {
      task.done = check.checked;
      if (task.done && currentTaskId === task.id) currentTaskId = null;
      persistTasks();
      renderTasks();
      renderTimer();
    });

    const title = document.createElement('button');
    title.type = 'button';
    title.className = 'task-title';
    title.textContent = task.title;
    title.title = t('tasks.select');
    title.addEventListener('click', () => {
      if (task.done) return;
      currentTaskId = currentTaskId === task.id ? null : task.id;
      persistTasks();
      renderTasks();
      renderTimer();
    });

    const pomos = document.createElement('span');
    pomos.className = 'task-pomos';
    pomos.textContent = task.pomos ? `${task.pomos} ×` : '';

    const del = document.createElement('button');
    del.type = 'button';
    del.className = 'icon-btn task-del';
    del.title = t('tasks.delete');
    del.setAttribute('aria-label', t('tasks.delete'));
    del.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
    del.addEventListener('click', () => {
      tasks = tasks.filter((x) => x.id !== task.id);
      if (currentTaskId === task.id) currentTaskId = null;
      persistTasks();
      renderTasks();
      renderTimer();
    });

    li.append(check, title, pomos, del);
    frag.append(li);
  }
  el.taskList.append(frag);
  el.taskEmpty.hidden = tasks.length > 0;
  el.clearDone.hidden = !tasks.some((x) => x.done);

  const atLimit = !pro() && tasks.length >= CONFIG.limits.freeTasks;
  el.taskLimit.hidden = !atLimit;
  if (atLimit) {
    el.taskLimit.innerHTML = '';
    el.taskLimit.append(document.createTextNode(t('tasks.limit', { n: CONFIG.limits.freeTasks }) + ' '));
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'link';
    b.textContent = t('btn.upgrade');
    b.addEventListener('click', () => openDialog(el.dlgPro));
    el.taskLimit.append(b);
  }
  el.taskInput.disabled = atLimit;
}

function renderToday() {
  const today = todayTotals(sessions);
  el.todaySessions.textContent = String(today.sessions);
  el.todayMinutes.textContent = String(today.minutes);
  if (pro()) {
    el.goalText.textContent = `${today.sessions}/${settings.dailyGoal}`;
    el.streakText.textContent = `${streak(sessions, { goal: settings.dailyGoal })}`;
    el.goalCell.classList.remove('is-locked');
    el.streakCell.classList.remove('is-locked');
  } else {
    el.goalText.textContent = '–';
    el.streakText.textContent = '–';
  }
  const rows = dailyTotals(sessions, { days: 7 });
  const max = Math.max(1, ...rows.map((r) => r.minutes));
  el.weekBars.innerHTML = '';
  rows.forEach((r, i) => {
    const s = document.createElement('span');
    s.style.height = `${Math.max(8, (r.minutes / max) * 100)}%`;
    s.dataset.v = r.minutes ? '1' : '0';
    if (i === rows.length - 1) s.classList.add('is-today');
    s.title = `${r.day}: ${r.minutes} min`;
    el.weekBars.append(s);
  });
}

function renderPro() {
  const on = pro();
  el.proPill.classList.toggle('is-pro', on);
  $$('.pro-field').forEach((f) => f.classList.toggle('is-locked', !on));
  $('#s-accent').disabled = !on;
  $('#pro-buy').hidden = on;
  $('#pro-active').hidden = !on;
  if (on) {
    const lic = getLicense();
    const d = lic?.activatedAt ? new Date(lic.activatedAt).toLocaleDateString() : '';
    $('#pro-since').textContent = [lic?.email, d && t('pro.activeSince', { date: d })].filter(Boolean).join(' · ');
  }
  const buy = $('#btn-buy');
  const price = CONFIG.price[getLang()] || CONFIG.price.en;
  if (CONFIG.checkoutUrl) {
    buy.href = CONFIG.checkoutUrl;
    buy.textContent = t('pro.buy', { price });
    buy.removeAttribute('aria-disabled');
  } else {
    buy.href = '#';
    buy.textContent = `${t('pro.buySoon')} · ${price}`;
    buy.setAttribute('aria-disabled', 'true');
  }
  const sup = $('#pro-support');
  sup.hidden = !CONFIG.supportEmail;
  if (CONFIG.supportEmail) sup.textContent = t('pro.support', { email: CONFIG.supportEmail });
}

function renderAll() {
  applyTheme();
  renderTimer();
  renderTasks();
  renderToday();
  renderPro();
  renderSettingsForm();
}

// ---------- timer events ----------
function recordSession({ mode, startedAt, endedAt, minutes }) {
  const task = currentTask();
  sessions.push({ id: uid(), start: startedAt, end: endedAt, mode, minutes, task: task ? task.title : '' });
  if (mode === 'focus' && task) task.pomos = (task.pomos || 0) + 1;
  persistSessions();
  persistTasks();
}

function notify(title) {
  if (!settings.notifications || !('Notification' in window) || Notification.permission !== 'granted') return;
  try {
    const n = new Notification(title, {
      body: t('notif.body', { n: todayTotals(sessions).sessions }),
      icon: './icons/icon-192.png',
      tag: 'doro',
      silent: true,
    });
    setTimeout(() => n.close(), 8000);
  } catch { /* some browsers only allow SW notifications */ }
}

function syncAmbient() {
  if (pro() && timer.running && timer.mode === 'focus' && settings.ambient !== 'off') {
    ambient.start(settings.ambient, settings.ambientVolume);
  } else {
    ambient.stop();
  }
}

timer.subscribe((e) => {
  switch (e.type) {
    case 'complete': {
      recordSession({ mode: e.finished, startedAt: e.startedAt, endedAt: e.endedAt, minutes: e.minutes });
      playChime(settings.sound, settings.volume);
      notify(e.finished === 'focus' ? t('notif.focusDone') : t('notif.breakDone'));
      const autoNext = pro() && (e.next === 'focus' ? settings.autoStartFocus : settings.autoStartBreaks);
      if (autoNext) setTimeout(() => { timer.start(); }, 1200);
      break;
    }
    case 'skip': {
      if (e.skipped === 'focus' && e.elapsedMs >= 60_000 && e.startedAt) {
        recordSession({ mode: 'focus', startedAt: e.startedAt, endedAt: e.endedAt, minutes: Math.round(e.elapsedMs / 60_000) });
      }
      break;
    }
    default:
      break;
  }
  if (e.type !== 'tick') persistTimer();
  renderTimer();
  if (e.type === 'complete' || e.type === 'skip') { renderTasks(); renderToday(); }
  syncAmbient();
});

setInterval(() => timer.tick(), 250);
document.addEventListener('visibilitychange', () => { if (!document.hidden) timer.tick(); });

// ---------- controls ----------
function startTimer() {
  unlockAudio();
  if (settings.notifications && 'Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission().catch(() => {});
  }
  timer.start();
}

el.toggle.addEventListener('click', () => (timer.running ? timer.pause() : startTimer()));
el.reset.addEventListener('click', () => timer.reset());
el.skip.addEventListener('click', () => timer.skip());
el.modes.forEach((b) => b.addEventListener('click', () => timer.setMode(b.dataset.mode)));

// tasks
el.taskForm.addEventListener('submit', (ev) => {
  ev.preventDefault();
  const title = el.taskInput.value.trim();
  if (!title) return;
  if (!pro() && tasks.length >= CONFIG.limits.freeTasks) { openDialog(el.dlgPro); return; }
  const task = { id: uid(), title, done: false, pomos: 0, createdAt: Date.now() };
  tasks.push(task);
  if (!currentTaskId) currentTaskId = task.id;
  el.taskInput.value = '';
  persistTasks();
  renderTasks();
  renderTimer();
});
el.clearDone.addEventListener('click', () => {
  tasks = tasks.filter((x) => !x.done);
  persistTasks();
  renderTasks();
});

// keyboard
document.addEventListener('keydown', (ev) => {
  if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
  const tag = (ev.target.tagName || '').toLowerCase();
  const typing = tag === 'input' || tag === 'textarea' || tag === 'select' || ev.target.isContentEditable;
  if (typing) {
    if (ev.key === 'Escape' && ev.target === el.taskInput) el.taskInput.blur();
    return;
  }
  if (anyDialogOpen()) return;
  switch (ev.key) {
    case ' ': ev.preventDefault(); timer.running ? timer.pause() : startTimer(); break;
    case 'r': case 'R': timer.reset(); break;
    case 'n': case 'N': timer.skip(); break;
    case '1': timer.setMode('focus'); break;
    case '2': timer.setMode('short'); break;
    case '3': timer.setMode('long'); break;
    case 't': case 'T': ev.preventDefault(); el.taskInput.focus(); break;
    case 's': case 'S': openSettings(); break;
    case 'd': case 'D': openStats(); break;
    case 'p': case 'P': openDialog(el.dlgPro); break;
    case '?': openDialog(el.dlgHelp); break;
    default: break;
  }
});

// dialogs: close buttons, backdrop click, open-pro buttons
$$('dialog').forEach((dlg) => {
  dlg.addEventListener('click', (ev) => { if (ev.target === dlg) dlg.close(); });
  $$('[data-close]', dlg).forEach((b) => b.addEventListener('click', () => dlg.close()));
});
$$('[data-open-pro]').forEach((b) => b.addEventListener('click', () => openDialog(el.dlgPro)));
$('#btn-settings').addEventListener('click', openSettings);
$('#btn-stats').addEventListener('click', openStats);
el.proPill.addEventListener('click', () => openDialog(el.dlgPro));
$('#btn-help').addEventListener('click', () => openDialog(el.dlgHelp));
$('#btn-lang').addEventListener('click', () => {
  settings.lang = getLang() === 'ko' ? 'en' : 'ko';
  saveSettings(settings);
  applyLang();
});
[el.goalCell, el.streakCell].forEach((c) => c.addEventListener('click', () => { if (!pro()) openDialog(el.dlgPro); }));

// ---------- settings ----------
const sf = {
  focus: $('#s-focus'), short: $('#s-short'), long: $('#s-long'), every: $('#s-every'),
  autoBreaks: $('#s-auto-breaks'), autoFocus: $('#s-auto-focus'),
  sound: $('#s-sound'), volume: $('#s-volume'), notifications: $('#s-notifications'), title: $('#s-title'),
  ambient: $('#s-ambient'), ambientVolume: $('#s-ambient-volume'),
  theme: $('#s-theme'), accent: $('#s-accent'), lang: $('#s-lang'), goal: $('#s-goal'),
};

function renderSettingsForm() {
  sf.focus.value = settings.durations.focus;
  sf.short.value = settings.durations.short;
  sf.long.value = settings.durations.long;
  sf.every.value = settings.longBreakEvery;
  sf.autoBreaks.checked = settings.autoStartBreaks;
  sf.autoFocus.checked = settings.autoStartFocus;
  sf.sound.value = settings.sound;
  sf.volume.value = settings.volume;
  sf.notifications.checked = settings.notifications;
  sf.title.checked = settings.titleCountdown;
  sf.ambient.value = settings.ambient;
  sf.ambientVolume.value = settings.ambientVolume;
  sf.theme.value = settings.theme;
  sf.accent.value = pro() ? settings.accent : 'classic';
  sf.lang.value = settings.lang;
  sf.goal.value = settings.dailyGoal;
  $('#version').textContent = CONFIG.version;
  $('#notif-denied').hidden = !('Notification' in window) || Notification.permission !== 'denied';
  renderPresets();
}

function clampInt(v, min, max, fallback) {
  const n = parseInt(v, 10);
  if (Number.isNaN(n)) return fallback;
  return Math.min(max, Math.max(min, n));
}

function readDurations() {
  settings.durations = {
    focus: clampInt(sf.focus.value, 1, 180, settings.durations.focus),
    short: clampInt(sf.short.value, 1, 60, settings.durations.short),
    long: clampInt(sf.long.value, 1, 90, settings.durations.long),
  };
  settings.longBreakEvery = clampInt(sf.every.value, 1, 12, settings.longBreakEvery);
  timer.setDurations(settings.durations);
  timer.setLongBreakEvery(settings.longBreakEvery);
  saveSettings(settings);
  renderPresets();
}
[sf.focus, sf.short, sf.long, sf.every].forEach((i) => i.addEventListener('change', readDurations));

sf.autoBreaks.addEventListener('change', () => { settings.autoStartBreaks = sf.autoBreaks.checked; saveSettings(settings); });
sf.autoFocus.addEventListener('change', () => { settings.autoStartFocus = sf.autoFocus.checked; saveSettings(settings); });
sf.sound.addEventListener('change', () => { settings.sound = sf.sound.value; saveSettings(settings); });
sf.volume.addEventListener('input', () => { settings.volume = parseFloat(sf.volume.value); saveSettings(settings); });
$('#btn-sound-test').addEventListener('click', () => { unlockAudio(); playChime(settings.sound, settings.volume); });
sf.notifications.addEventListener('change', () => {
  settings.notifications = sf.notifications.checked;
  saveSettings(settings);
  if (settings.notifications && 'Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission().then(() => renderSettingsForm()).catch(() => {});
  }
});
sf.title.addEventListener('change', () => { settings.titleCountdown = sf.title.checked; saveSettings(settings); renderTimer(); });
sf.ambient.addEventListener('change', () => {
  settings.ambient = sf.ambient.value;
  saveSettings(settings);
  unlockAudio();
  // Preview for a moment even when idle so the user can hear the choice.
  if (settings.ambient !== 'off' && pro()) {
    ambient.start(settings.ambient, settings.ambientVolume);
    if (!(timer.running && timer.mode === 'focus')) setTimeout(() => syncAmbient(), 4000);
  } else syncAmbient();
});
sf.ambientVolume.addEventListener('input', () => {
  settings.ambientVolume = parseFloat(sf.ambientVolume.value);
  saveSettings(settings);
  ambient.setVolume(settings.ambientVolume);
});
sf.theme.addEventListener('change', () => { settings.theme = sf.theme.value; saveSettings(settings); applyTheme(); });
sf.accent.addEventListener('change', () => { settings.accent = sf.accent.value; saveSettings(settings); applyTheme(); });
sf.lang.addEventListener('change', () => { settings.lang = sf.lang.value; saveSettings(settings); applyLang(); });
sf.goal.addEventListener('change', () => { settings.dailyGoal = clampInt(sf.goal.value, 1, 30, 8); saveSettings(settings); renderToday(); });
$$('.pro-field').forEach((f) => f.addEventListener('click', (ev) => {
  if (f.classList.contains('is-locked')) { ev.preventDefault(); openDialog(el.dlgPro); }
}));
sf.accent.parentElement.addEventListener('click', () => { if (!pro()) openDialog(el.dlgPro); });

function renderPresets() {
  const list = $('#preset-list');
  list.innerHTML = '';
  const d = settings.durations;
  for (const p of settings.presets) {
    const chip = document.createElement('span');
    chip.className = 'preset' + (p.focus === d.focus && p.short === d.short && p.long === d.long ? ' is-active' : '');
    const apply = document.createElement('button');
    apply.type = 'button';
    apply.className = 'link';
    apply.style.textDecoration = 'none';
    apply.innerHTML = `<b></b> ${p.focus}/${p.short}/${p.long}`;
    apply.querySelector('b').textContent = p.name;
    apply.addEventListener('click', () => {
      settings.durations = { focus: p.focus, short: p.short, long: p.long };
      timer.setDurations(settings.durations);
      saveSettings(settings);
      renderSettingsForm();
      renderTimer();
    });
    const del = document.createElement('button');
    del.type = 'button';
    del.setAttribute('aria-label', t('tasks.delete'));
    del.textContent = '×';
    del.addEventListener('click', () => {
      settings.presets = settings.presets.filter((x) => x !== p);
      saveSettings(settings);
      renderPresets();
    });
    chip.append(apply, del);
    list.append(chip);
  }
  const atLimit = !pro() && settings.presets.length >= CONFIG.limits.freeCustomPresets;
  $('#preset-limit').hidden = !atLimit;
  $('#btn-preset-save').disabled = atLimit;
}
$('#btn-preset-save').addEventListener('click', () => {
  if (!pro() && settings.presets.length >= CONFIG.limits.freeCustomPresets) { openDialog(el.dlgPro); return; }
  const nameInput = $('#preset-name');
  const name = nameInput.value.trim() || `${settings.durations.focus}/${settings.durations.short}/${settings.durations.long}`;
  settings.presets.push({ name, ...settings.durations });
  nameInput.value = '';
  saveSettings(settings);
  renderPresets();
});

$('#btn-wipe').addEventListener('click', () => {
  if (!confirm(t('settings.resetConfirm'))) return;
  ['settings', 'tasks', 'sessions', 'currentTask', 'timer'].forEach(remove);
  location.reload();
});

function openSettings() {
  renderSettingsForm();
  openDialog(el.dlgSettings);
}

// ---------- stats ----------
function bar(row, max, isToday, labelFn) {
  const b = document.createElement('div');
  b.className = 'bar' + (isToday ? ' is-today' : '');
  b.dataset.v = row.minutes ? '1' : '0';
  b.title = `${row.day}: ${row.minutes} min · ${row.sessions} ${t('stats.sessions')}`;
  const v = document.createElement('b');
  v.textContent = row.minutes ? String(row.minutes) : '';
  const i = document.createElement('i');
  i.style.height = `${Math.max(2, (row.minutes / max) * 100)}%`;
  const s = document.createElement('small');
  s.textContent = labelFn(row);
  b.append(v, i, s);
  return b;
}

function openStats() {
  const on = pro();
  const today = todayTotals(sessions);
  const weekRows = dailyTotals(sessions, { days: 7 });
  const weekTotal = weekRows.reduce((a, r) => ({ minutes: a.minutes + r.minutes, sessions: a.sessions + r.sessions }), { minutes: 0, sessions: 0 });
  const all = totals(sessions);

  const fmt = (m) => (m >= 120 ? `${(m / 60).toFixed(1)}${t('stats.hours')}` : `${m} ${t('stats.minutes')}`);
  const grid = $('#stats-grid');
  grid.innerHTML = '';
  const cells = [
    [t('stats.today'), today],
    [t('stats.week'), weekTotal],
    [t('stats.all'), on ? all : null],
  ];
  for (const [label, v] of cells) {
    const d = document.createElement('div');
    const n = document.createElement('div');
    n.className = 'stat-num';
    n.textContent = v ? fmt(v.minutes) : '–';
    const l = document.createElement('div');
    l.className = 'stat-label';
    l.textContent = v ? `${label} · ${v.sessions} ${t('stats.sessions')}` : label;
    d.append(n, l);
    grid.append(d);
  }

  const weekdays = getLang() === 'ko' ? ['일', '월', '화', '수', '목', '금', '토'] : ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const chartW = $('#chart-week');
  chartW.innerHTML = '';
  const maxW = Math.max(1, ...weekRows.map((r) => r.minutes));
  weekRows.forEach((r, i) => chartW.append(bar(r, maxW, i === weekRows.length - 1, (row) => weekdays[new Date(row.ts).getDay()])));

  $('#stats-pro').hidden = !on;
  $('#stats-locked').hidden = on;
  if (on) {
    const monthRows = dailyTotals(sessions, { days: 30 });
    const chartM = $('#chart-month');
    chartM.innerHTML = '';
    const maxM = Math.max(1, ...monthRows.map((r) => r.minutes));
    monthRows.forEach((r, i) => chartM.append(bar(r, maxM, i === monthRows.length - 1, (row) => String(new Date(row.ts).getDate()))));
  }
  $('#stats-empty').hidden = sessions.some((s) => s.mode === 'focus');
  openDialog(el.dlgStats);
}

$('#btn-export').addEventListener('click', () => {
  const blob = new Blob([toCSV(sessions)], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `doro-sessions-${dayKey(Date.now())}.csv`;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
});

// ---------- pro / license ----------
$('#license-form').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const btn = $('#btn-activate');
  const msg = $('#license-msg');
  const key = $('#license-key').value;
  btn.disabled = true;
  btn.textContent = t('pro.activating');
  msg.className = 'small';
  msg.textContent = '';
  const r = await activate(key);
  btn.disabled = false;
  btn.textContent = t('pro.activate');
  if (r.ok) {
    msg.className = 'small ok';
    msg.textContent = t('pro.active');
    $('#license-key').value = '';
    renderAll();
    toast(t('pro.active'));
  } else {
    msg.className = 'small err';
    msg.textContent = r.error === 'network' ? t('pro.errNetwork') : t('pro.errInvalid');
  }
});
$('#btn-deactivate').addEventListener('click', async () => {
  await deactivate();
  renderAll();
});

// ---------- service worker ----------
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').then((reg) => {
      reg.addEventListener('updatefound', () => {
        const nw = reg.installing;
        nw?.addEventListener('statechange', () => {
          if (nw.state === 'installed' && navigator.serviceWorker.controller) {
            toast(t('update.ready'), { action: t('update.reload'), onAction: () => location.reload(), sticky: true });
          }
        });
      });
    }).catch(() => {});
  });
}

// ---------- boot ----------
applyLang();
timer.restore(load('timer', null));
renderAll();
revalidate().then(() => renderAll());
window.addEventListener('online', () => revalidate());

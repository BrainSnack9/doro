// All sound is synthesised with the Web Audio API — no audio files, works offline.

let ctx = null;

function getCtx() {
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
  }
  if (ctx.state === 'suspended') ctx.resume().catch(() => {});
  return ctx;
}

/** Call from a user gesture once so browsers allow playback later. */
export function unlockAudio() {
  getCtx();
}

function tone(ac, { freq, start, duration, volume, type = 'sine', decay = true }) {
  const osc = ac.createOscillator();
  const gain = ac.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, start);
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(volume, start + 0.01);
  if (decay) gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
  else gain.gain.setValueAtTime(volume, start + duration - 0.02), gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
  osc.connect(gain).connect(ac.destination);
  osc.start(start);
  osc.stop(start + duration + 0.05);
}

const CHIMES = {
  chime: (ac, t0, v) => {
    [523.25, 659.25, 783.99].forEach((f, i) => tone(ac, { freq: f, start: t0 + i * 0.12, duration: 0.9, volume: v }));
  },
  bell: (ac, t0, v) => {
    tone(ac, { freq: 880, start: t0, duration: 1.6, volume: v, type: 'sine' });
    tone(ac, { freq: 1760, start: t0, duration: 0.8, volume: v * 0.35, type: 'sine' });
    tone(ac, { freq: 2637, start: t0, duration: 0.4, volume: v * 0.15, type: 'sine' });
  },
  digital: (ac, t0, v) => {
    for (let i = 0; i < 3; i++) tone(ac, { freq: 1046.5, start: t0 + i * 0.18, duration: 0.1, volume: v * 0.6, type: 'square', decay: false });
  },
};

export function playChime(kind = 'chime', volume = 0.6) {
  if (kind === 'none') return;
  const ac = getCtx();
  if (!ac) return;
  const fn = CHIMES[kind] || CHIMES.chime;
  fn(ac, ac.currentTime + 0.02, Math.max(0.0001, Math.min(1, volume)));
}

// ---------- Ambient noise ----------

function makeBuffer(ac, seconds, fill) {
  const buf = ac.createBuffer(2, Math.floor(ac.sampleRate * seconds), ac.sampleRate);
  for (let ch = 0; ch < 2; ch++) fill(buf.getChannelData(ch), ac.sampleRate, ch);
  return buf;
}

function brownNoise(data) {
  let last = 0;
  for (let i = 0; i < data.length; i++) {
    const white = Math.random() * 2 - 1;
    last = (last + 0.02 * white) / 1.02;
    data[i] = last * 3.5;
  }
}

function pinkNoise(data) {
  // Paul Kellet's refined method
  let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
  for (let i = 0; i < data.length; i++) {
    const w = Math.random() * 2 - 1;
    b0 = 0.99886 * b0 + w * 0.0555179;
    b1 = 0.99332 * b1 + w * 0.0750759;
    b2 = 0.96900 * b2 + w * 0.1538520;
    b3 = 0.86650 * b3 + w * 0.3104856;
    b4 = 0.55000 * b4 + w * 0.5329522;
    b5 = -0.7616 * b5 - w * 0.0168980;
    data[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + w * 0.5362) * 0.11;
    b6 = w * 0.115926;
  }
}

function rainNoise(data, rate) {
  // Hiss bed + sparse random droplets with a short decay.
  let hp = 0, prev = 0;
  for (let i = 0; i < data.length; i++) {
    const w = Math.random() * 2 - 1;
    hp = 0.97 * (hp + w - prev); // one-pole high-pass
    prev = w;
    data[i] = hp * 0.12;
  }
  const drops = Math.floor((data.length / rate) * 35);
  for (let d = 0; d < drops; d++) {
    const pos = Math.floor(Math.random() * (data.length - 2000));
    const amp = 0.15 + Math.random() * 0.35;
    const len = 200 + Math.floor(Math.random() * 900);
    for (let i = 0; i < len; i++) {
      const env = Math.exp(-i / (len * 0.25));
      data[pos + i] += (Math.random() * 2 - 1) * amp * env;
    }
  }
}

function cafeNoise(data, rate) {
  // Pink murmur with slow swells + occasional clinks.
  pinkNoise(data);
  for (let i = 0; i < data.length; i++) {
    const t = i / rate;
    const swell = 0.6 + 0.4 * Math.sin(t * 0.7) * Math.sin(t * 0.23 + 1.3);
    data[i] *= swell * 0.9;
  }
  const clinks = Math.floor((data.length / rate) * 0.6);
  for (let c = 0; c < clinks; c++) {
    const pos = Math.floor(Math.random() * (data.length - 4000));
    const f = 2200 + Math.random() * 2500;
    for (let i = 0; i < 3000; i++) {
      data[pos + i] += Math.sin((2 * Math.PI * f * i) / rate) * 0.08 * Math.exp(-i / 500);
    }
  }
}

const GENERATORS = { brown: brownNoise, rain: rainNoise, cafe: cafeNoise };

export class Ambient {
  constructor() {
    this.kind = 'off';
    this.source = null;
    this.gain = null;
    this.filter = null;
    this.volume = 0.4;
    this.buffers = new Map();
  }

  get playing() {
    return !!this.source;
  }

  setVolume(v) {
    this.volume = v;
    if (this.gain) this.gain.gain.setTargetAtTime(v, getCtx().currentTime, 0.05);
  }

  start(kind, volume = this.volume) {
    if (kind === 'off' || !GENERATORS[kind]) { this.stop(); return; }
    const ac = getCtx();
    if (!ac) return;
    if (this.playing && this.kind === kind) { this.setVolume(volume); return; }
    this.stop(true);
    this.kind = kind;
    this.volume = volume;
    let buf = this.buffers.get(kind);
    if (!buf) {
      buf = makeBuffer(ac, 8, (data, rate) => GENERATORS[kind](data, rate));
      this.buffers.set(kind, buf);
    }
    const src = ac.createBufferSource();
    src.buffer = buf;
    src.loop = true;
    const filter = ac.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = kind === 'cafe' ? 1800 : kind === 'rain' ? 9000 : 500;
    const gain = ac.createGain();
    gain.gain.setValueAtTime(0.0001, ac.currentTime);
    gain.gain.exponentialRampToValueAtTime(Math.max(0.0001, volume), ac.currentTime + 1.2);
    src.connect(filter).connect(gain).connect(ac.destination);
    src.start();
    this.source = src;
    this.gain = gain;
    this.filter = filter;
  }

  stop(immediate = false) {
    if (!this.source) return;
    const ac = getCtx();
    const src = this.source;
    const gain = this.gain;
    this.source = null;
    this.gain = null;
    if (immediate || !ac) {
      try { src.stop(); } catch { /* already stopped */ }
      return;
    }
    gain.gain.cancelScheduledValues(ac.currentTime);
    gain.gain.setTargetAtTime(0.0001, ac.currentTime, 0.25);
    setTimeout(() => { try { src.stop(); } catch { /* ignore */ } }, 1200);
  }
}

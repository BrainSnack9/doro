// Pro licensing via the Lemon Squeezy License API.
// The key is activated once per browser ("instance") and re-validated at most weekly.
// Nothing here is a security boundary — Doro is honour-system, like most indie apps.
import { CONFIG } from './config.js';
import { load, save, remove, uid } from './store.js';

const REVALIDATE_MS = 7 * 24 * 60 * 60 * 1000;

export function getLicense() {
  return load('license', null);
}

export function isPro() {
  const l = getLicense();
  return !!(l && l.status === 'active' && l.key);
}

function instanceName() {
  let id = load('instance', null);
  if (!id) {
    id = `doro-${uid()}`;
    save('instance', id);
  }
  const ua = navigator.userAgent || '';
  const browser = /Edg\//.test(ua) ? 'Edge' : /Chrome\//.test(ua) ? 'Chrome' : /Safari\//.test(ua) ? 'Safari' : /Firefox\//.test(ua) ? 'Firefox' : 'Browser';
  return `${browser} ${id}`;
}

async function post(path, params) {
  const res = await fetch(`${CONFIG.licenseApi}/${path}`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
    body: new URLSearchParams(params),
  });
  const data = await res.json().catch(() => ({}));
  return { status: res.status, data };
}

/** @returns {Promise<{ok:true}|{ok:false,error:'invalid'|'network'}>} */
export async function activate(rawKey) {
  const key = String(rawKey || '').trim();
  if (!key) return { ok: false, error: 'invalid' };
  let r;
  try {
    r = await post('activate', { license_key: key, instance_name: instanceName() });
  } catch {
    return { ok: false, error: 'network' };
  }
  const { data } = r;
  if (data && data.activated) {
    save('license', {
      key,
      instanceId: data.instance?.id || null,
      status: 'active',
      email: data.meta?.customer_email || null,
      activatedAt: Date.now(),
      validatedAt: Date.now(),
    });
    return { ok: true };
  }
  // Lemon Squeezy answers {activated:false, error:"..."} for bad keys / no activations left.
  return { ok: false, error: 'invalid' };
}

/** Periodically confirm the key is still valid. Network failures never revoke. */
export async function revalidate(force = false) {
  const l = getLicense();
  if (!l || !l.key) return;
  if (!force && Date.now() - (l.validatedAt || 0) < REVALIDATE_MS) return;
  if (!navigator.onLine) return;
  try {
    const params = { license_key: l.key };
    if (l.instanceId) params.instance_id = l.instanceId;
    const { data } = await post('validate', params);
    if (data && typeof data.valid === 'boolean') {
      save('license', { ...l, status: data.valid ? 'active' : 'invalid', validatedAt: Date.now() });
    }
  } catch {
    /* offline or blocked — keep current state */
  }
}

export async function deactivate() {
  const l = getLicense();
  if (l && l.key && l.instanceId) {
    try { await post('deactivate', { license_key: l.key, instance_id: l.instanceId }); } catch { /* best effort */ }
  }
  remove('license');
}

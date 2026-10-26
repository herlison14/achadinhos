// ---- Seguranca das APIs do painel: chave + codigo de 2 fatores + bloqueio ---------
// Cole este bloco acima de `export default {` (depois dos blocos 1 e 2) e troque as duas rotas por:
//   if (url.pathname === '/api/cliques') return protegido(req, env, url, apiCliques);
//   if (url.pathname === '/api/ganhos') return protegido(req, env, url, ganhosApi);
//
// Segredos do Worker:
//   REPORT_KEY   (ja existe)  a chave do relatorio
//   TOTP_SECRET  (novo)       segredo base32 do app autenticador. Se nao existir, o 2o fator fica desligado.
// O painel envia no cabecalho:  Authorization: Bearer <chave><codigo de 6 digitos>
//
// Defesas: 5 erros em 15 min por IP => 429 por 15 min (mesmo acertando depois); so o hash do IP e
// guardado (tabela `tentativas` no D1); comparacao por SHA-256; codigo valido por 30 s (+-1 janela).

const TENTATIVAS_MAX = 5;
const JANELA_MIN = 15;

async function sha256Hex(txt) {
  const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(txt));
  return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, '0')).join('');
}

function base32(s) {
  const A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '';
  for (const c of s.toUpperCase().replace(/[^A-Z2-7]/g, '')) bits += A.indexOf(c).toString(2).padStart(5, '0');
  const out = new Uint8Array(Math.floor(bits.length / 8));
  for (let i = 0; i < out.length; i++) out[i] = parseInt(bits.slice(i * 8, i * 8 + 8), 2);
  return out;
}

async function totp(segredo, contador) {
  const key = await crypto.subtle.importKey('raw', base32(segredo), { name: 'HMAC', hash: 'SHA-1' }, false, ['sign']);
  const msg = new Uint8Array(8);
  let c = contador;
  for (let i = 7; i >= 0; i--) { msg[i] = c & 0xff; c = Math.floor(c / 256); }
  const h = new Uint8Array(await crypto.subtle.sign('HMAC', key, msg));
  const o = h[19] & 15;
  const n = ((h[o] & 0x7f) << 24) | (h[o + 1] << 16) | (h[o + 2] << 8) | h[o + 3];
  return String(n % 1000000).padStart(6, '0');
}

async function codigoOk(segredo, codigo, agora) {
  if (!/^\d{6}$/.test(codigo)) return false;
  const c = Math.floor(agora / 30);
  let ok = false;
  for (const d of [-1, 0, 1]) if ((await totp(segredo, c + d)) === codigo) ok = true;
  return ok;
}

async function autorizar(req, env, h) {
  const jerr = (obj, status, extra) =>
    new Response(JSON.stringify(obj), { status, headers: { ...h, ...(extra || {}), 'Content-Type': 'application/json; charset=utf-8' } });

  if (!env.REPORT_KEY) return jerr({ erro: 'servidor sem chave configurada' }, 503);

  const ip = req.headers.get('CF-Connecting-IP') || 'sem-ip';
  const id = (await sha256Hex(env.REPORT_KEY + '|' + ip)).slice(0, 32);
  const agora = Math.floor(Date.now() / 1000);
  const janela = JANELA_MIN * 60;

  await env.DB.prepare(
    'CREATE TABLE IF NOT EXISTS tentativas (id TEXT PRIMARY KEY, n INTEGER NOT NULL, inicio INTEGER NOT NULL)'
  ).run();

  const reg = await env.DB.prepare('SELECT n, inicio FROM tentativas WHERE id = ?').bind(id).first();
  if (reg && agora - reg.inicio < janela && reg.n >= TENTATIVAS_MAX) {
    const espera = Math.max(1, janela - (agora - reg.inicio));
    return jerr({ erro: 'muitas tentativas; aguarde ' + Math.ceil(espera / 60) + ' min' }, 429, { 'Retry-After': String(espera) });
  }

  const auth = req.headers.get('Authorization') || '';
  let k = auth.startsWith('Bearer ') ? auth.slice(7) : '';
  let dois = true;
  if (env.TOTP_SECRET) {
    dois = await codigoOk(env.TOTP_SECRET, k.slice(-6), agora);
    k = k.slice(0, -6);
  }
  const [a, b] = await Promise.all([sha256Hex(k), sha256Hex(env.REPORT_KEY)]);
  if (k && a === b && dois) {
    if (reg) await env.DB.prepare('DELETE FROM tentativas WHERE id = ?').bind(id).run();
    return null;
  }

  await env.DB.prepare(
    'INSERT INTO tentativas (id, n, inicio) VALUES (?, 1, ?) ' +
      'ON CONFLICT (id) DO UPDATE SET n = CASE WHEN ? - inicio >= ? THEN 1 ELSE n + 1 END, ' +
      'inicio = CASE WHEN ? - inicio >= ? THEN ? ELSE inicio END'
  ).bind(id, agora, agora, janela, agora, janela, agora).run();
  await env.DB.prepare('DELETE FROM tentativas WHERE inicio < ?').bind(agora - 86400).run();
  return jerr({ erro: 'nao autorizado' }, 401);
}

// Porteiro das rotas: confere chave + codigo, e entrega a rota original com a chave "limpa".
async function protegido(req, env, url, rota) {
  if (req.method === 'OPTIONS') return rota(req, env, url);
  const neg = await autorizar(req, env, corsApi(req.headers.get('Origin')));
  if (neg) return neg;
  const hd = new Headers(req.headers);
  hd.set('Authorization', 'Bearer ' + env.REPORT_KEY);
  return rota(new Request(req, { headers: hd }), env, url);
}

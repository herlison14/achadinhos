// ---- Seguranca das APIs do painel ------------------------------------------------
// autorizar(): confere a REPORT_KEY e bloqueia tentativa de adivinhar a chave.
//  - 5 erros em 15 min vindos do mesmo IP => 429 por 15 min (mesmo com a chave certa).
//  - o IP nunca e guardado: so um hash (SHA-256 com a propria chave como sal).
//  - chave e comparada por hash (tempo constante, sem vazar o tamanho).
// Retorna null se autorizado; senao, a Response de erro. Precisa de D1 (env.DB).
const TENTATIVAS_MAX = 5;
const JANELA_MIN = 15;

async function sha256Hex(txt) {
  const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(txt));
  return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, '0')).join('');
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
  const viva = reg && agora - reg.inicio < janela;
  if (viva && reg.n >= TENTATIVAS_MAX) {
    const espera = Math.max(1, janela - (agora - reg.inicio));
    return jerr({ erro: 'muitas tentativas; aguarde ' + Math.ceil(espera / 60) + ' min' }, 429, { 'Retry-After': String(espera) });
  }

  const auth = req.headers.get('Authorization') || '';
  const k = auth.startsWith('Bearer ') ? auth.slice(7) : '';
  const [a, b] = await Promise.all([sha256Hex(k), sha256Hex(env.REPORT_KEY)]);
  if (k && a === b) {
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

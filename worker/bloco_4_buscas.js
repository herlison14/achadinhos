// ---- Buscas sem resultado (lista de "procurados") --------------------------------
// Cole este bloco acima de `export default {` (depois dos blocos 1, 2 e 3) e acrescente as rotas,
// logo depois de `const url = new URL(req.url);`:
//   if (url.pathname === '/b') return buscaRegistrar(req, env);
//   if (url.pathname === '/api/buscas') return protegido(req, env, url, apiBuscas);
//
// O site manda so o termo digitado (quando a busca nao achou nada). Nada de IP, cookie ou
// identificacao de quem buscou. Tabela `buscas` (dia, termo, n) criada sozinha no D1.
// Limites contra abuso: termo de 3 a 60 caracteres, no maximo 400 termos diferentes por dia
// (depois disso so soma nos que ja existem).

const BUSCAS_DIA_MAX = 400;

function normalizarTermo(t) {
  return String(t || '')
    .toLowerCase()
    .normalize('NFC')
    .replace(/[^\p{L}\p{N} .,\-+/]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 60);
}

async function tabelaBuscas(env) {
  await env.DB.prepare('CREATE TABLE IF NOT EXISTS buscas (dia TEXT NOT NULL, termo TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (dia, termo))').run();
}

async function buscaRegistrar(req, env) {
  const origem = req.headers.get('Origin') || '';
  const h = { 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Cache-Control': 'no-store', Vary: 'Origin' };
  if (SITES.includes(origem)) h['Access-Control-Allow-Origin'] = origem;
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: h });
  if (req.method !== 'POST') return new Response('Metodo nao permitido', { status: 405, headers: h });
  if (origem && !SITES.includes(origem)) return new Response(null, { status: 204, headers: h });

  let termo = '';
  try {
    const corpo = await req.text();
    if (corpo.length > 300) return new Response(null, { status: 204, headers: h });
    termo = normalizarTermo(JSON.parse(corpo).t);
  } catch (e) {
    return new Response(null, { status: 204, headers: h });
  }
  if (termo.length < 3) return new Response(null, { status: 204, headers: h });

  await tabelaBuscas(env);
  const dia = hojeBrasilia(0);
  const existe = await env.DB.prepare('SELECT 1 FROM buscas WHERE dia = ? AND termo = ?').bind(dia, termo).first();
  if (existe) {
    await env.DB.prepare('UPDATE buscas SET n = n + 1 WHERE dia = ? AND termo = ?').bind(dia, termo).run();
  } else {
    const c = await env.DB.prepare('SELECT COUNT(*) AS t FROM buscas WHERE dia = ?').bind(dia).first();
    if ((c && c.t) < BUSCAS_DIA_MAX) {
      await env.DB.prepare('INSERT INTO buscas (dia, termo, n) VALUES (?, ?, 1)').bind(dia, termo).run();
    }
  }
  return new Response(null, { status: 204, headers: h });
}

// GET /api/buscas?dias=7 (painel, aba Procurados). Protegido por chave + 2FA via protegido().
async function apiBuscas(req, env, url) {
  const h = corsApi(req.headers.get('Origin'));
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: h });
  if (req.method !== 'GET') return new Response('Metodo nao permitido', { status: 405, headers: h });
  const auth = req.headers.get('Authorization') || '';
  const k = auth.startsWith('Bearer ') ? auth.slice(7) : '';
  if (!env.REPORT_KEY || !k || !iguais(k, env.REPORT_KEY)) {
    return new Response(JSON.stringify({ erro: 'nao autorizado' }), { status: 401, headers: { ...h, 'Content-Type': 'application/json' } });
  }
  let dias = parseInt(url.searchParams.get('dias') || '7', 10);
  if (!(dias >= 1)) dias = 7;
  if (dias > 90) dias = 90;
  const desde = hojeBrasilia(dias - 1);
  await tabelaBuscas(env);
  const r = await env.DB.batch([
    env.DB.prepare('SELECT COALESCE(SUM(n),0) AS t, COUNT(DISTINCT termo) AS d FROM buscas WHERE dia >= ?').bind(desde),
    env.DB.prepare('SELECT termo AS nome, SUM(n) AS n, MAX(dia) AS ultimo FROM buscas WHERE dia >= ? GROUP BY termo ORDER BY n DESC, ultimo DESC LIMIT 60').bind(desde),
  ]);
  const corpo = { desde, dias, total: r[0].results[0].t, termos: r[0].results[0].d, lista: r[1].results };
  return new Response(JSON.stringify(corpo), { headers: { ...h, 'Content-Type': 'application/json; charset=utf-8' } });
}

// ---- API JSON do painel (GET /api/cliques) ----------------------------------
// Auth: cabecalho Authorization: Bearer <REPORT_KEY>. A chave nunca vai na URL.
const PAINEL = ['https://achadinhos-4tf.pages.dev', ...SITES];

function corsApi(origin) {
  const h = {
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Authorization, Content-Type',
    'Access-Control-Max-Age': '600',
    'Cache-Control': 'no-store',
    Vary: 'Origin',
  };
  if (origin && PAINEL.includes(origin)) h['Access-Control-Allow-Origin'] = origin;
  return h;
}

function iguais(a, b) {
  if (a.length !== b.length) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}

async function apiCliques(req, env, url) {
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

  const q = (sql) => env.DB.prepare(sql).bind(desde);
  const r = await env.DB.batch([
    q('SELECT COALESCE(SUM(n),0) AS t FROM cliques WHERE dia >= ?'),
    q('SELECT dia AS nome, SUM(n) AS n FROM cliques WHERE dia >= ? GROUP BY dia ORDER BY dia DESC'),
    q('SELECT loja AS nome, SUM(n) AS n FROM cliques WHERE dia >= ? GROUP BY loja ORDER BY n DESC'),
    q('SELECT origem AS nome, SUM(n) AS n FROM cliques WHERE dia >= ? GROUP BY origem ORDER BY n DESC'),
    q('SELECT categoria AS nome, SUM(n) AS n FROM cliques WHERE dia >= ? GROUP BY categoria ORDER BY n DESC'),
    q('SELECT produto AS nome, loja, SUM(n) AS n FROM cliques WHERE dia >= ? GROUP BY produto, loja ORDER BY n DESC LIMIT 30'),
  ]);

  const corpo = {
    desde,
    dias,
    total: r[0].results[0].t,
    porDia: r[1].results,
    lojas: r[2].results,
    origens: r[3].results,
    categorias: r[4].results,
    produtos: r[5].results,
  };
  return new Response(JSON.stringify(corpo), { headers: { ...h, 'Content-Type': 'application/json; charset=utf-8' } });
}


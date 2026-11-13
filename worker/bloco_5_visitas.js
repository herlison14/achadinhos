// ---- Visitas reais e funil (aba Funil do painel) -----------------------------------
// Cole este bloco acima de `export default {` (depois dos blocos 1 a 4) e acrescente as rotas,
// logo depois de `const url = new URL(req.url);`:
//   if (url.pathname === '/v') return visitaRegistrar(req, env);
//   if (url.pathname === '/api/funil') return protegido(req, env, url, apiFunil);
//
// Por que existe: o Analytics do Cloudflare conta tudo, inclusive robos (EUA, Holanda, Polonia...
// procurando /.env). O cliques.js so avisa /v quando um navegador de verdade abre a pagina
// (JavaScript rodando, pagina visivel, sem navigator.webdriver). Nada de IP, cookie ou
// identificacao: so dia, origem (ig, wa, tg, anuncio, direto...), tipo de pagina e se e a
// 1a pagina da sessao (= 1 visita). Tabela `visitas` criada sozinha no D1.

const VISITA_ORIGEM = /^[a-z0-9_-]{1,20}$/;
const VISITA_PAGINA = ['home', 'oferta', 'loja', 'natal', 'outra'];
const VISITA_COMBOS_DIA_MAX = 300; // contra abuso: combinacoes (origem, pagina) novas por dia

async function tabelaVisitas(env) {
  await env.DB.prepare(
    'CREATE TABLE IF NOT EXISTS visitas (dia TEXT NOT NULL, origem TEXT NOT NULL, pagina TEXT NOT NULL, ' +
      'sessoes INTEGER NOT NULL DEFAULT 0, views INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (dia, origem, pagina))'
  ).run();
}

async function visitaRegistrar(req, env) {
  const origem = req.headers.get('Origin') || '';
  const h = { 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Cache-Control': 'no-store', Vary: 'Origin' };
  if (SITES.includes(origem)) h['Access-Control-Allow-Origin'] = origem;
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: h });
  if (req.method !== 'POST') return new Response('Metodo nao permitido', { status: 405, headers: h });
  if (!SITES.includes(origem)) return new Response(null, { status: 204, headers: h }); // so do proprio site

  let o = 'direto', p = 'outra', s = 0;
  try {
    const corpo = await req.text();
    if (corpo.length > 200) return new Response(null, { status: 204, headers: h });
    const d = JSON.parse(corpo);
    if (VISITA_ORIGEM.test(String(d.o || ''))) o = String(d.o);
    if (VISITA_PAGINA.includes(d.p)) p = d.p;
    s = d.s === 1 ? 1 : 0;
  } catch (e) {
    return new Response(null, { status: 204, headers: h });
  }

  await tabelaVisitas(env);
  const dia = hojeBrasilia(0);
  const existe = await env.DB.prepare('SELECT 1 FROM visitas WHERE dia = ? AND origem = ? AND pagina = ?').bind(dia, o, p).first();
  if (existe) {
    await env.DB.prepare('UPDATE visitas SET sessoes = sessoes + ?, views = views + 1 WHERE dia = ? AND origem = ? AND pagina = ?')
      .bind(s, dia, o, p).run();
  } else {
    const c = await env.DB.prepare('SELECT COUNT(*) AS t FROM visitas WHERE dia = ?').bind(dia).first();
    if ((c && c.t) < VISITA_COMBOS_DIA_MAX) {
      await env.DB.prepare('INSERT INTO visitas (dia, origem, pagina, sessoes, views) VALUES (?, ?, ?, ?, 1)').bind(dia, o, p, s).run();
    }
  }
  return new Response(null, { status: 204, headers: h });
}

// GET /api/funil?dias=30 — visitas reais, cliques nas lojas e pedidos (se a aba Ganhos tiver CSV).
// Devolve so contagens. Comissao (R$) nao sai por aqui.
async function apiFunil(req, env, url) {
  const h = corsApi(req.headers.get('Origin'));
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: h });
  if (req.method !== 'GET') return new Response('Metodo nao permitido', { status: 405, headers: h });
  const auth = req.headers.get('Authorization') || '';
  const k = auth.startsWith('Bearer ') ? auth.slice(7) : '';
  if (!env.REPORT_KEY || !k || !iguais(k, env.REPORT_KEY)) {
    return new Response(JSON.stringify({ erro: 'nao autorizado' }), { status: 401, headers: { ...h, 'Content-Type': 'application/json' } });
  }
  let dias = parseInt(url.searchParams.get('dias') || '30', 10);
  if (!(dias >= 1)) dias = 30;
  if (dias > 365) dias = 365;
  const desde = hojeBrasilia(dias - 1);
  await tabelaVisitas(env);

  const q = (sql) => env.DB.prepare(sql).bind(desde);
  const r = await env.DB.batch([
    q('SELECT dia, SUM(sessoes) AS visitas, SUM(views) AS views FROM visitas WHERE dia >= ? GROUP BY dia'),
    q('SELECT dia, SUM(n) AS cliques FROM cliques WHERE dia >= ? GROUP BY dia'),
    q('SELECT origem AS nome, SUM(sessoes) AS visitas FROM visitas WHERE dia >= ? GROUP BY origem'),
    q('SELECT origem AS nome, SUM(n) AS cliques FROM cliques WHERE dia >= ? GROUP BY origem'),
    q('SELECT pagina AS nome, SUM(views) AS views FROM visitas WHERE dia >= ? GROUP BY pagina ORDER BY views DESC'),
    q('SELECT MIN(dia) AS d FROM visitas WHERE dia >= ?'),
  ]);

  let pedidos = [];
  try {
    const g = await env.DB.prepare('SELECT dia, loja, SUM(pedidos) AS pedidos FROM ganhos WHERE dia >= ? GROUP BY dia, loja').bind(desde).all();
    pedidos = g.results || [];
  } catch (e) {} // tabela ganhos ainda nao existe

  const corpo = {
    desde,
    dias,
    inicioVisitas: (r[5].results[0] || {}).d || null,
    visitasDia: r[0].results,
    cliquesDia: r[1].results,
    visitasOrigem: r[2].results,
    cliquesOrigem: r[3].results,
    paginas: r[4].results,
    pedidos,
  };
  return new Response(JSON.stringify(corpo), { headers: { ...h, 'Content-Type': 'application/json; charset=utf-8' } });
}

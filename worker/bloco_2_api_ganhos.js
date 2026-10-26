// ---- Ganhos (comissao) no D1: GET e POST /api/ganhos --------------------------
// Mesma auth do /api/cliques: Authorization: Bearer <REPORT_KEY>. Os valores ficam
// so no banco D1 (privado); nada de comissao vai para o repositorio publico.
const LOJAS_G = ['shopee', 'amazon', 'meli', 'aliexpress', 'magalu'];

function corsGanhos(origin) {
  const h = {
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Authorization, Content-Type',
    'Access-Control-Max-Age': '600',
    'Cache-Control': 'no-store',
    Vary: 'Origin',
  };
  if (origin && PAINEL.includes(origin)) h['Access-Control-Allow-Origin'] = origin;
  return h;
}

function jsonG(obj, status, h) {
  return new Response(JSON.stringify(obj), { status: status || 200, headers: { ...h, 'Content-Type': 'application/json; charset=utf-8' } });
}

async function ganhosApi(req, env, url) {
  const h = corsGanhos(req.headers.get('Origin'));
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: h });
  if (req.method !== 'GET' && req.method !== 'POST') return new Response('Metodo nao permitido', { status: 405, headers: h });

  const auth = req.headers.get('Authorization') || '';
  const k = auth.startsWith('Bearer ') ? auth.slice(7) : '';
  if (!env.REPORT_KEY || !k || !iguais(k, env.REPORT_KEY)) return jsonG({ erro: 'nao autorizado' }, 401, h);

  await env.DB.prepare(
    'CREATE TABLE IF NOT EXISTS ganhos (dia TEXT NOT NULL, loja TEXT NOT NULL, produto TEXT NOT NULL, ' +
      'pedidos INTEGER NOT NULL DEFAULT 0, comissao REAL NOT NULL DEFAULT 0, PRIMARY KEY (dia, loja, produto))'
  ).run();

  if (req.method === 'POST') {
    let corpo;
    try {
      const texto = await req.text();
      if (texto.length > 600000) return jsonG({ erro: 'arquivo grande demais' }, 413, h);
      corpo = JSON.parse(texto);
    } catch (e) {
      return jsonG({ erro: 'json invalido' }, 400, h);
    }
    const linhas = Array.isArray(corpo && corpo.linhas) ? corpo.linhas : null;
    if (!linhas || !linhas.length) return jsonG({ erro: 'sem linhas' }, 400, h);
    if (linhas.length > 3000) return jsonG({ erro: 'mais de 3000 linhas' }, 400, h);

    const ok = [];
    const erros = [];
    linhas.forEach((l, i) => {
      const dia = String((l && l.dia) || '');
      const loja = String((l && l.loja) || '');
      const produto = limpar(l && l.produto, 120);
      const pedidos = Number(l && l.pedidos);
      const comissao = Number(l && l.comissao);
      const d = new Date(dia + 'T00:00:00Z');
      if (!/^\d{4}-\d{2}-\d{2}$/.test(dia) || isNaN(d.getTime())) return erros.push('linha ' + (i + 1) + ': data invalida');
      if (!LOJAS_G.includes(loja)) return erros.push('linha ' + (i + 1) + ': loja invalida');
      if (!produto) return erros.push('linha ' + (i + 1) + ': produto vazio');
      if (!Number.isInteger(pedidos) || pedidos < 0 || pedidos > 100000) return erros.push('linha ' + (i + 1) + ': pedidos invalido');
      if (!isFinite(comissao) || comissao < 0 || comissao > 1000000) return erros.push('linha ' + (i + 1) + ': comissao invalida');
      ok.push([dia, loja, produto, pedidos, Math.round(comissao * 100) / 100]);
    });
    if (erros.length) return jsonG({ erro: 'nada foi gravado', detalhes: erros.slice(0, 20), total_erros: erros.length }, 400, h);

    const sql =
      'INSERT INTO ganhos (dia, loja, produto, pedidos, comissao) VALUES (?, ?, ?, ?, ?) ' +
      'ON CONFLICT (dia, loja, produto) DO UPDATE SET pedidos = excluded.pedidos, comissao = excluded.comissao';
    for (let i = 0; i < ok.length; i += 100) {
      await env.DB.batch(ok.slice(i, i + 100).map((r) => env.DB.prepare(sql).bind(r[0], r[1], r[2], r[3], r[4])));
    }
    return jsonG({ gravadas: ok.length }, 200, h);
  }

  let dias = parseInt(url.searchParams.get('dias') || '30', 10);
  if (!(dias >= 1)) dias = 30;
  if (dias > 365) dias = 365;
  const desde = hojeBrasilia(dias - 1);
  const q = (sql) => env.DB.prepare(sql).bind(desde);
  const r = await env.DB.batch([
    q('SELECT COALESCE(SUM(comissao),0) AS c, COALESCE(SUM(pedidos),0) AS p FROM ganhos WHERE dia >= ?'),
    q('SELECT dia AS nome, SUM(comissao) AS c, SUM(pedidos) AS p FROM ganhos WHERE dia >= ? GROUP BY dia ORDER BY dia DESC'),
    q('SELECT loja AS nome, SUM(comissao) AS c, SUM(pedidos) AS p FROM ganhos WHERE dia >= ? GROUP BY loja ORDER BY c DESC'),
    q('SELECT produto AS nome, loja, SUM(comissao) AS c, SUM(pedidos) AS p FROM ganhos WHERE dia >= ? GROUP BY produto, loja ORDER BY c DESC LIMIT 30'),
    q('SELECT loja AS nome, SUM(n) AS n FROM cliques WHERE dia >= ? GROUP BY loja'),
  ]);
  return jsonG({
    desde,
    dias,
    comissao: r[0].results[0].c,
    pedidos: r[0].results[0].p,
    porDia: r[1].results,
    lojas: r[2].results,
    produtos: r[3].results,
    cliquesPorLoja: r[4].results,
  }, 200, h);
}


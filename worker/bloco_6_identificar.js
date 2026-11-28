// ---- Identificar produto por foto (caixa "Procura um produto específico?" do site) ------------
// Cole este bloco acima de `export default {` (depois dos blocos 1 a 5) e acrescente a rota,
// logo depois de `const url = new URL(req.url);`:
//   if (url.pathname === '/identificar') return identificarProduto(req, env);
//
// REQUISITOS (uma vez só):
//  1) Vinculação do Workers AI: Cloudflare > Workers > cliques-binga > Configurações > Vinculações >
//     Adicionar > Workers AI, com o nome de variavel  AI  (a documentacao da Cloudflare mostra o
//     binding "AI" no arquivo do Wrangler; no painel o caminho pode ter outro nome de menu).
//  2) Aceite de licenca do modelo da Meta, primeira vez (a documentacao pede uma chamada de aceite):
//       curl https://api.cloudflare.com/client/v4/accounts/<ID_DA_CONTA>/ai/run/@cf/meta/llama-3.2-11b-vision-instruct \
//         -X POST -H "Authorization: Bearer <TOKEN_DE_API_COM_WORKERS_AI>" -d '{ "prompt": "agree" }'
//     (so ele faz isso; o token nao vai para o repositorio nem para o chat.)
//  3) Conferir o plano/custo do Workers AI no painel antes de divulgar; os limites abaixo seguram o uso.
//
// O QUE FAZ: recebe do site UMA foto ja reduzida (JPEG, ate 768 px, sem EXIF, a data URL e feita no
// navegador), pede ao modelo so o NOME do produto e devolve { nome }. A foto NAO e gravada em lugar
// nenhum (nem D1, nem log). O modelo nunca devolve link nem preco: o site monta a busca nas lojas.
// Limites contra abuso e custo: tamanho da imagem, total de identificacoes por dia e por visitante.
// Para o limite por visitante guardamos so um codigo irreversivel (hash do IP + dia) e a contagem,
// na tabela `ident_uso`, apagada no dia seguinte. Nada de IP em claro.

const IDENT_MODELO = '@cf/meta/llama-3.2-11b-vision-instruct';
const IDENT_IMG_MAX = 450000; // caracteres da data URL (~330 KB)
const IDENT_DIA_MAX = 300; // identificacoes por dia, somando todos
const IDENT_VISITANTE_DIA = 8; // por visitante por dia

const IDENT_SISTEMA =
  'You identify consumer products in photos for a Brazilian shopping website. Reply ONLY with JSON.';
const IDENT_PEDIDO =
  'If the photo shows a single consumer product that can be bought online, reply with exactly this JSON ' +
  'and nothing else: {"nome":"<product type plus brand and model only if clearly visible, in Brazilian ' +
  'Portuguese, at most 8 words>"}. Do not describe people, places or unrelated text. If you cannot tell, ' +
  'reply {"nome":""}.';

function identResp(origem, status, corpo) {
  const h = {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    Vary: 'Origin',
  };
  if (SITES.includes(origem)) h['Access-Control-Allow-Origin'] = origem;
  return new Response(corpo === null ? null : JSON.stringify(corpo), { status, headers: h });
}

// Limpa o que o modelo devolveu: so letras, numeros e pontuacao simples; sem link; ate 60 caracteres.
function identLimpar(t) {
  let s = String(t || '')
    .normalize('NFC')
    .replace(/[^\p{L}\p{N} .,\-+/&']/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 60)
    .trim();
  if (/https?|www\.|\.com|\.br/i.test(s)) return '';
  if (s.length < 3) return '';
  return s;
}

function identNomeDaResposta(r) {
  let txt = '';
  if (typeof r === 'string') txt = r;
  else if (r && typeof r === 'object') {
    const v = r.response !== undefined ? r.response : r.result !== undefined ? r.result : r.description;
    txt = typeof v === 'string' ? v : v && typeof v === 'object' ? JSON.stringify(v) : '';
  }
  const m = txt.match(/\{[\s\S]*?\}/);
  if (m) {
    try {
      const j = JSON.parse(m[0]);
      if (j && typeof j.nome === 'string') return identLimpar(j.nome);
    } catch (e) {}
  }
  return '';
}

async function identCodigo(ip, dia) {
  const dados = new TextEncoder().encode('ident|' + dia + '|' + ip);
  const h = new Uint8Array(await crypto.subtle.digest('SHA-256', dados));
  let s = '';
  for (let i = 0; i < 8; i++) s += h[i].toString(16).padStart(2, '0');
  return s;
}

async function identificarProduto(req, env) {
  const origem = req.headers.get('Origin') || '';
  if (req.method === 'OPTIONS') return identResp(origem, 204, null);
  if (req.method !== 'POST') return identResp(origem, 405, { erro: 'metodo' });
  if (!SITES.includes(origem)) return identResp(origem, 403, { erro: 'origem' }); // so do proprio site
  if (!env.AI) return identResp(origem, 503, { erro: 'indisponivel' });

  let img = '';
  try {
    const corpo = await req.text();
    if (corpo.length > IDENT_IMG_MAX + 100) return identResp(origem, 413, { erro: 'grande' });
    img = String(JSON.parse(corpo).img || '');
  } catch (e) {
    return identResp(origem, 400, { erro: 'corpo' });
  }
  if (img.length > IDENT_IMG_MAX || !/^data:image\/jpeg;base64,[A-Za-z0-9+/]+={0,2}$/.test(img)) {
    return identResp(origem, 400, { erro: 'imagem' });
  }

  // limites (sem IP em claro; contagem apagada no dia seguinte)
  await env.DB.prepare(
    'CREATE TABLE IF NOT EXISTS ident_uso (dia TEXT NOT NULL, quem TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (dia, quem))'
  ).run();
  const dia = hojeBrasilia(0);
  await env.DB.prepare('DELETE FROM ident_uso WHERE dia < ?').bind(dia).run();
  const quem = await identCodigo(req.headers.get('CF-Connecting-IP') || 'sem-ip', dia);
  const r = await env.DB.batch([
    env.DB.prepare("SELECT COALESCE(SUM(n),0) AS t FROM ident_uso WHERE dia = ? AND quem = '*'").bind(dia),
    env.DB.prepare('SELECT COALESCE(SUM(n),0) AS t FROM ident_uso WHERE dia = ? AND quem = ?').bind(dia, quem),
  ]);
  if (r[0].results[0].t >= IDENT_DIA_MAX || r[1].results[0].t >= IDENT_VISITANTE_DIA) {
    return identResp(origem, 429, { erro: 'limite' });
  }
  for (const k of ['*', quem]) {
    await env.DB.prepare(
      'INSERT INTO ident_uso (dia, quem, n) VALUES (?, ?, 1) ON CONFLICT(dia, quem) DO UPDATE SET n = n + 1'
    )
      .bind(dia, k)
      .run();
  }

  let nome = '';
  try {
    const saida = await env.AI.run(IDENT_MODELO, {
      messages: [
        { role: 'system', content: IDENT_SISTEMA },
        { role: 'user', content: IDENT_PEDIDO },
      ],
      image: img,
      max_tokens: 80,
    });
    nome = identNomeDaResposta(saida);
  } catch (e) {
    // sem gravar a foto nem o conteudo: so o tipo do erro, para achar o motivo em Observabilidade
    console.log('identificar: falha do modelo (' + String((e && e.message) || e).slice(0, 120) + ')');
    return identResp(origem, 503, { erro: 'indisponivel' });
  }
  return identResp(origem, 200, { nome });
}

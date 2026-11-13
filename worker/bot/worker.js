// Worker `bot-binga`: responde mensagens diretas do Telegram e do Instagram com ofertas REAIS de dados/itens.json.
// Regras: só mostra preço quando o item foi conferido há no máximo 7 dias (e diz a data); itens sem conferência
// há mais de 30 dias não aparecem; nunca inventa desconto, estoque ou avaliação; toda resposta leva
// "Publicidade: links de afiliado"; não guarda mensagens nem dados de quem escreve; não fala de comissão.
// Rotas:  POST /telegram   (webhook do Telegram, cabeçalho X-Telegram-Bot-Api-Secret-Token = TG_SECRET)
//         GET/POST /instagram (webhook da Meta: verificação por IG_VERIFY, assinatura X-Hub-Signature-256 com META_APP_SECRET)
//         Campos do webhook: `messages` (DM) e `comments` (comentário nos posts: responde em público e, se a pessoa
//         pediu o link, manda no direct com as ofertas daquele post, pela resposta privada oficial da Meta).
// Segredos (Cloudflare > Worker > Configurações > Variáveis, tipo Segredo): TELEGRAM_TOKEN, TG_SECRET,
//         META_APP_SECRET, IG_VERIFY, IG_PAGE_TOKEN. Nenhum deles vai para o repositório.
const REPO = 'herlison14/achadinhos';
const ITENS = 'https://raw.githubusercontent.com/' + REPO + '/main/dados/itens.json';
const SITE = 'https://achadinhosdobinga.com.br';
const AVISO = 'Publicidade: links de afiliado.';
const LOJAS = { amazon: 'Amazon', magalu: 'Magalu', meli: 'Mercado Livre', shopee: 'Shopee', aliexpress: 'AliExpress', kabum: 'KaBuM!', nike: 'Nike', dafiti: 'Dafiti', adidas: 'adidas', docebeleza: 'Doce Beleza', puma: 'PUMA', hope: 'Hope Lingerie', mizuno: 'Mizuno', polishop: 'Polishop' };
const DIAS_PRECO = 7, DIAS_PAGINA = 30, MAX = 3;
const POSTS = 'https://raw.githubusercontent.com/' + REPO + '/main/dados/posts.json';

let cache = { t: 0, itens: [] };
let contaIg = '';           // id da conta do Instagram (vem em cada aviso da Meta); o login do Instagram não aceita /me/messages
let cachePosts = { t: 0, posts: [] };
const publicas = [];       // horas das respostas públicas (no máximo 30 por hora, para não parecer spam)
const vistos = new Map();   // id de mensagem -> hora (evita responder duas vezes quando a Meta reenvia)
const ritmo = new Map();    // remetente -> horas das últimas respostas (no máximo 8 por minuto)

export function norm(s) {
  return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/&amp;/g, ' ').replace(/[^a-z0-9 ]/g, ' ').replace(/\s+/g, ' ').trim();
}
const PARADAS = new Set('o a os as um uma de do da dos das para pra por com sem quero queria busco procuro tem tenho voce vcs link links preco precos oi ola bom boa dia tarde noite me manda mande passa passe favor por'.split(' '));
const SINONIMOS = { fritadeira: 'airfryer air fryer', airfryer: 'fritadeira air fryer', natal: 'natal natalino', pelucia: 'pelucia', brinquedo: 'brinquedo infantil boneca lego', celular: 'celular smartphone' };

export function idade(conferido, agora = new Date()) {
  const d = new Date(conferido + 'T12:00:00-03:00');
  return Math.floor((agora - d) / 86400000);
}
export function dataBR(iso) { const [a, m, d] = iso.split('-'); return d + '/' + m + '/' + a; }
export function html(s) { return String(s || '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'"); }

export function buscar(texto, itens, agora = new Date(), max = MAX) {
  let termos = norm(texto).split(' ').filter((t) => t.length > 1 && !PARADAS.has(t));
  termos = [...new Set(termos.flatMap((t) => (SINONIMOS[t] ? [t, ...SINONIMOS[t].split(' ')] : [t])))];
  if (!termos.length) return [];
  const pontos = itens.filter((i) => idade(i.conferido, agora) <= DIAS_PAGINA).map((i) => {
    const pal = norm(html(i.nome)).split(' '), outras = (norm(i.cat) + ' ' + norm(LOJAS[i.loja] || i.loja)).split(' ');
    let p = 0;
    for (const t of termos) {
      if (pal.includes(t)) p += 3;
      else if (t.length >= 4 && pal.some((w) => w.startsWith(t) || (w.length >= 4 && t.startsWith(w)))) p += 2;
      else if (outras.some((w) => w === t || (t.length >= 4 && w.startsWith(t)))) p += 1;
    }
    return { i, p };
  }).filter((x) => x.p > 0);
  pontos.sort((a, b) => b.p - a.p || (a.i.conferido < b.i.conferido ? 1 : a.i.conferido > b.i.conferido ? -1 : 0));
  // no máximo 1 item por loja nas primeiras posições, para a pessoa poder comparar
  const out = [], lojas = new Set();
  for (const x of pontos) { if (!lojas.has(x.i.loja)) { out.push(x.i); lojas.add(x.i.loja); } if (out.length === max) break; }
  for (const x of pontos) { if (out.length === max) break; if (!out.includes(x.i)) out.push(x.i); }
  return out;
}

export function linhaItem(i, agora = new Date()) {
  const loja = LOJAS[i.loja] || i.loja;
  const preco = idade(i.conferido, agora) <= DIAS_PRECO
    ? 'R$ ' + i.preco + ' (conferido em ' + dataBR(i.conferido) + ')'
    : 'preço na loja (última conferência em ' + dataBR(i.conferido) + ')';
  return '• ' + html(i.nome) + '\n  ' + loja + ' — ' + preco + '\n  ' + i.href;
}

export function responder(texto, itens, agora = new Date(), limiteChars = 3900) {
  const n = norm(texto);
  if (/^(parar|sair|stop|cancelar)$/.test(n)) return 'Tudo bem, não envio mais nada. Se quiser voltar, é só escrever o nome de um produto. ' + AVISO;
  const soParadas = n.split(' ').filter((t) => t.length > 1 && !PARADAS.has(t)).length === 0;   // ex.: só "quero" ou "link": ainda não disse o produto
  if (!n || soParadas || /^(oi|ola|menu|ajuda|start|help|bom dia|boa tarde|boa noite)$/.test(n))
    return 'Oi! Eu sou o robô do Achadinhos do Binga. Escreva o produto que você procura (ex.: "air fryer", "árvore de natal", "lego") e eu mostro opções conferidas, com link.\nTudo organizado por categoria: ' + SITE + '\n' + AVISO;
  let r = buscar(texto, itens, agora);
  if (!r.length)
    return 'Não achei esse produto entre as ofertas conferidas. Veja todas por categoria e loja: ' + SITE + '\nTente outra palavra (ex.: "cafeteira", "brinquedo", "decoração"). ' + AVISO;
  const montar = (l) => 'Achei estas opções:\n\n' + l.map((i) => linhaItem(i, agora)).join('\n\n') + '\n\nMais ofertas: ' + SITE + '\nPreço e estoque podem mudar na loja. ' + AVISO;
  while (r.length > 1 && montar(r).length > limiteChars) r = r.slice(0, -1);   // cabe no limite do canal, sem cortar o aviso
  return montar(r);
}


// ---------- Comentários nos posts ----------
// Pedido de link/preço: "quero", "link", "preço", "onde compra"... (texto já normalizado, sem acento)
export function gatilho(texto) {
  const n = ' ' + norm(texto) + ' ';
  return /\b(quero|queria|link|links|preco|precos|valor|quanto|onde|comprar|compro|manda|mande|passa|passe|cade|disponivel|tem)\b/.test(n);
}
// Não responde sozinho: reclamação, golpe, ofensa, link/@ de terceiros, só emoji. Vai para revisão humana.
export function seguro(texto) {
  const t = String(texto || '');
  if (!/[a-zA-ZÀ-ÿ]/.test(t)) return false;
  if (/https?:|www\.|\.com\b|@\w/i.test(t)) return false;
  if (/\b(golpe|fake|fraude|procon|reclame|enganacao|lixo|roubo|ladr|processo|denunci)/.test(norm(t))) return false;
  return true;
}
const PUBLICAS_GATILHO = ['Te mandei no direct! 📩', 'Mandei os links no seu direct 📩', 'Enviei no direct, dá uma olhada 📩'];
const PUBLICAS_GERAL = [
  'Valeu pelo comentário! 💛 Se quiser o link de algum produto, é só comentar QUERO.',
  'Obrigado por passar por aqui! 😊 Quer o link? Comenta QUERO que eu mando no direct.',
  'Que bom ter você aqui! Quer ver mais ofertas conferidas? Tem tudo no link da bio 🔗',
];
function escolhe(lista, id) { let h = 0; for (const c of String(id)) h = (h * 31 + c.charCodeAt(0)) >>> 0; return lista[h % lista.length]; }

// Ofertas do post comentado (posts.json: ig_id -> produtos). Cabe nos 1000 caracteres do direct.
export function respostaDoPost(post, itens, agora = new Date(), limiteChars = 950) {
  const por = new Map(itens.map((i) => [i.id, i]));
  let lista = ((post && post.produtos) || []).map((id) => por.get(id)).filter((i) => i && idade(i.conferido, agora) <= DIAS_PAGINA);
  if (!lista.length) return null;
  const montar = (l, mais) => 'Oi! Aqui estão os links do post 👇\n\n' + l.map((i) => linhaItem(i, agora)).join('\n\n') + '\n\n' + (mais ? 'Tem mais no site: ' : 'Mais ofertas: ') + SITE + '\nPreço e estoque podem mudar na loja. ' + AVISO;
  let l = lista.slice();
  while (l.length > 1 && montar(l, l.length < lista.length).length > limiteChars) l = l.slice(0, -1);
  return montar(l, l.length < lista.length);
}
export function respostaPrivada(textoComentario, post, itens, agora = new Date()) {
  const doPost = respostaDoPost(post, itens, agora);
  if (doPost) return doPost;
  if (buscar(textoComentario, itens, agora).length) return responder(textoComentario, itens, agora, 900);
  return 'Oi! Aqui estão todas as ofertas conferidas, por categoria e loja: ' + SITE + '\nSe quiser, escreva o nome do produto (ex.: "air fryer") que eu mostro opções com link. ' + AVISO;
}
function podeResponderEmPublico() {
  const agora = Date.now();
  while (publicas.length && agora - publicas[0] > 3600000) publicas.shift();
  if (publicas.length >= 30) return false;
  publicas.push(agora); return true;
}
async function carregarPosts() {
  if (Date.now() - cachePosts.t < 10 * 60 * 1000 && cachePosts.posts.length) return cachePosts.posts;
  const r = await fetch(POSTS, { cf: { cacheTtl: 300 } });
  if (!r.ok) throw new Error('posts.json: HTTP ' + r.status);
  const j = await r.json();
  cachePosts = { t: Date.now(), posts: (Array.isArray(j) ? j : j.posts || []).filter((p) => p.ig_id).map(({ ig_id, produtos }) => ({ ig_id: String(ig_id), produtos: produtos || [] })) };
  return cachePosts.posts;
}
// Token do login do Instagram (começa com IGAA) fala com graph.instagram.com; token de Página (EAA) com graph.facebook.com.
function graphIg(env) {
  return String(env.IG_PAGE_TOKEN || '').startsWith('IGAA') ? 'https://graph.instagram.com/v21.0' : 'https://graph.facebook.com/v21.0';
}

async function motivo(r) {
  try { const j = await r.clone().json(); const e = j.error || {}; return ' [' + (e.type || '') + ' ' + (e.code || '') + (e.error_subcode ? '/' + e.error_subcode : '') + ': ' + String(e.message || '').slice(0, 200) + ']'; } catch (e) { return ''; }
}
async function igResponderComentario(env, comentario, texto) {
  const r = await fetch(graphIg(env) + '/' + comentario + '/replies', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + env.IG_PAGE_TOKEN, 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: texto }),
  });
  if (!r.ok) console.log('instagram: resposta ao comentário recusada HTTP ' + r.status + await motivo(r));
}
async function igRespostaPrivada(env, comentario, texto) {
  const r = await fetch(graphIg(env) + '/' + (contaIg || 'me') + '/messages', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + env.IG_PAGE_TOKEN, 'Content-Type': 'application/json' },
    body: JSON.stringify({ recipient: { comment_id: comentario }, message: { text: texto.slice(0, 1000) } }),
  });
  if (!r.ok) console.log('instagram: resposta privada recusada HTTP ' + r.status + await motivo(r));
  return r.ok;
}
async function tratarComentario(env, conta, v, itens) {
  if (!v || !v.id || !v.text || !v.from || v.parent_id) return;          // só comentário novo de primeiro nível
  if (v.from.id === conta || !novo('igc:' + v.id)) return;                // nunca responde a si mesmo nem repete
  if (!seguro(v.text)) { console.log('comentário para revisão humana: ' + v.id); return; }
  if (!limite('igc:' + v.from.id)) return;
  let enviouPrivada = false;
  if (gatilho(v.text)) {
    let posts = []; try { posts = await carregarPosts(); } catch (e) { console.log(String(e)); }
    const post = posts.find((p) => p.ig_id === String(v.media && v.media.id));
    enviouPrivada = await igRespostaPrivada(env, v.id, respostaPrivada(v.text, post, itens));
  }
  if (podeResponderEmPublico())
    await igResponderComentario(env, v.id, escolhe(enviouPrivada ? PUBLICAS_GATILHO : PUBLICAS_GERAL, v.id));
}

async function carregar() {
  if (Date.now() - cache.t < 10 * 60 * 1000 && cache.itens.length) return cache.itens;
  const r = await fetch(ITENS, { cf: { cacheTtl: 300 } });
  if (!r.ok) throw new Error('itens.json: HTTP ' + r.status);
  const j = await r.json();
  // adidas (Awin): os termos do programa não autorizam Telegram nem mensagem direta; fica só no site e no feed
  cache = { t: Date.now(), itens: (Array.isArray(j) ? j : j.itens || []).filter((i) => i.loja !== 'adidas').map(({ id, loja, cat, nome, href, preco, conferido }) => ({ id, loja, cat, nome, href, preco, conferido })) };
  return cache.itens;
}

function limite(quem) {
  const agora = Date.now(), l = (ritmo.get(quem) || []).filter((t) => agora - t < 60000);
  if (l.length >= 8) { ritmo.set(quem, l); return false; }
  l.push(agora); ritmo.set(quem, l);
  if (ritmo.size > 5000) ritmo.clear();
  return true;
}
function novo(id) {
  const agora = Date.now();
  for (const [k, t] of vistos) if (agora - t > 3600000) vistos.delete(k);
  if (vistos.has(id)) return false;
  vistos.set(id, agora); return true;
}

async function igEnviar(env, para, texto) {
  const r = await fetch(graphIg(env) + '/' + (contaIg || 'me') + '/messages', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + env.IG_PAGE_TOKEN, 'Content-Type': 'application/json' },
    body: JSON.stringify({ recipient: { id: para }, messaging_type: 'RESPONSE', message: { text: texto.slice(0, 1000) } }),
  });
  if (!r.ok) console.log('instagram: envio recusado HTTP ' + r.status + await motivo(r));
}
async function tgEnviar(env, chat, texto) {
  const r = await fetch('https://api.telegram.org/bot' + env.TELEGRAM_TOKEN + '/sendMessage', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chat, text: texto.slice(0, 4000), disable_web_page_preview: true }),
  });
  if (!r.ok) console.log('telegram: envio recusado HTTP ' + r.status + await motivo(r));
}

async function assinaturaOk(env, corpo, cab) {
  if (!env.META_APP_SECRET || !cab || !cab.startsWith('sha256=')) return false;
  const k = await crypto.subtle.importKey('raw', new TextEncoder().encode(env.META_APP_SECRET), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const s = new Uint8Array(await crypto.subtle.sign('HMAC', k, new TextEncoder().encode(corpo)));
  const hex = [...s].map((b) => b.toString(16).padStart(2, '0')).join('');
  const a = cab.slice(7); if (a.length !== hex.length) return false;
  let d = 0; for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ hex.charCodeAt(i);
  return d === 0;
}

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    if (url.pathname === '/instagram' && req.method === 'GET') {
      const ok = url.searchParams.get('hub.mode') === 'subscribe' && env.IG_VERIFY && url.searchParams.get('hub.verify_token') === env.IG_VERIFY;
      return ok ? new Response(url.searchParams.get('hub.challenge')) : new Response('negado', { status: 403 });
    }
    if (url.pathname === '/instagram' && req.method === 'POST') {
      const corpo = await req.text();
      if (!(await assinaturaOk(env, corpo, req.headers.get('X-Hub-Signature-256')))) return new Response('assinatura inválida', { status: 401 });
      ctx.waitUntil((async () => {
        let j; try { j = JSON.parse(corpo); } catch { return; }
        const itens = await carregar();
        if (j.entry && j.entry[0] && j.entry[0].id) contaIg = String(j.entry[0].id);
        for (const e of j.entry || []) for (const c of e.changes || []) {
          if (c.field === 'comments') await tratarComentario(env, e.id, c.value, itens);
        }
        for (const e of j.entry || []) for (const m of e.messaging || []) {
          const msg = m.message; if (!msg || msg.is_echo || !msg.text || !m.sender) continue;
          if (m.sender.id === e.id || !novo('ig:' + (msg.mid || m.timestamp))) continue;
          if (!limite('ig:' + m.sender.id)) continue;
          await igEnviar(env, m.sender.id, responder(msg.text, itens, new Date(), 900));
        }
      })());
      return new Response('ok');
    }
    if (url.pathname === '/telegram' && req.method === 'POST') {
      if (!env.TG_SECRET || req.headers.get('X-Telegram-Bot-Api-Secret-Token') !== env.TG_SECRET) return new Response('negado', { status: 403 });
      const u = await req.json().catch(() => null);
      const m = u && u.message;
      if (m && m.text && m.chat && m.chat.type === 'private' && novo('tg:' + u.update_id) && limite('tg:' + m.chat.id)) {
        ctx.waitUntil((async () => {
          const texto = m.text.replace(/^\/(start|ajuda|help)(@\w+)?/i, 'ajuda').replace(/^\/natal(@\w+)?/i, 'natal');
          await tgEnviar(env, m.chat.id, responder(texto, await carregar()));
        })());
      }
      return new Response('ok');
    }
    return new Response('Not found', { status: 404 });
  },
};

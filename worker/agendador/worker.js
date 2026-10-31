// Worker `agendador-binga`: acorda o robô do Instagram no minuto certo.
// O agendamento do GitHub Actions atrasa horas; o cron da Cloudflare não.
// A cada 10 minutos olha dados/posts.json (público) e, se houver post do Instagram
// "agendado" cujo horário (Brasília) já passou, dispara o workflow instagram.yml (acao=publicar).
// Segredo necessário: GH_TOKEN (token fine-grained só deste repositório, permissão Actions: leitura e escrita).
// Não guarda nem mostra nada além disso; não tem rotas públicas.
const REPO = 'herlison14/achadinhos';
const POSTS = 'https://raw.githubusercontent.com/' + REPO + '/main/dados/posts.json';

function agoraBrasilia() {
  // Brasil sem horário de verão: UTC-3 fixo. Formato AAAA-MM-DDTHH:MM para comparar como texto.
  return new Date(Date.now() - 3 * 3600 * 1000).toISOString().slice(0, 16);
}

async function devidos() {
  const r = await fetch(POSTS + '?t=' + Date.now(), { cf: { cacheTtl: 0 } });
  if (!r.ok) throw new Error('posts.json: HTTP ' + r.status);
  const agora = agoraBrasilia();
  return (await r.json()).filter(
    (p) => p.canal === 'ig' && p.status === 'agendado' && p.data && p.hora && p.data + 'T' + p.hora <= agora
  );
}

async function disparar(env) {
  const r = await fetch('https://api.github.com/repos/' + REPO + '/actions/workflows/instagram.yml/dispatches', {
    method: 'POST',
    headers: {
      Authorization: 'Bearer ' + env.GH_TOKEN,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'agendador-binga',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ ref: 'main', inputs: { acao: 'publicar' } }),
  });
  if (r.status !== 204) throw new Error('GitHub recusou o disparo: HTTP ' + r.status);
}

export default {
  async scheduled(event, env, ctx) {
    if (!env.GH_TOKEN) { console.log('sem GH_TOKEN'); return; }
    const fila = await devidos();
    if (!fila.length) { console.log('nada no horário'); return; }
    await disparar(env);
    console.log('disparado para: ' + fila.map((p) => p.id).join(', '));
  },
  async fetch() {
    return new Response('Not found', { status: 404 });
  },
};

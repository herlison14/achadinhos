# Blocos do Worker `cliques-binga`

O Worker publicado (Cloudflare) tem o contador de cliques (`POST /c`, `GET /relatorio`). Estes blocos são acréscimos, colados acima de `export default {`:

1. `bloco_1_api_cliques.js` — `GET /api/cliques` (JSON para o painel). Já publicado em 26/10/2026.
2. `bloco_2_api_ganhos.js` — `GET` e `POST /api/ganhos` (comissão no D1, tabela criada sozinha). Usa `PAINEL`, `iguais`, `hojeBrasilia` e `limpar`, definidos no código original e no bloco 1.

Rotas dentro do `fetch`, logo depois de `const url = new URL(req.url);`:

```js
if (url.pathname === '/api/cliques') return apiCliques(req, env, url);
if (url.pathname === '/api/ganhos') return ganhosApi(req, env, url);
```

Segurança: a chave (`REPORT_KEY`) é um segredo do Worker e vai no cabeçalho `Authorization: Bearer`, nunca na URL. Comissão fica só no D1, nunca neste repositório.

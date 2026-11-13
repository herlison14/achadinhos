# Blocos do Worker `cliques-binga`

O Worker publicado (Cloudflare) tem o contador de cliques (`POST /c`, `GET /relatorio`). Estes blocos são acréscimos, colados acima de `export default {`:

0. `bloco_3_seguranca.js` — `autorizar()`: bloqueia 15 min após 5 chaves erradas (por IP, só hash guardado, tabela `tentativas` no D1). Cole acima dos outros blocos; os blocos 1 e 2 já chamam `autorizar` (substitui `iguais`).
1. `bloco_1_api_cliques.js` — `GET /api/cliques` (JSON para o painel). Já publicado em 26/10/2026.
2. `bloco_2_api_ganhos.js` — `GET` e `POST /api/ganhos` (comissão no D1, tabela criada sozinha). Usa `PAINEL`, `iguais`, `hojeBrasilia` e `limpar`, definidos no código original e no bloco 1.
3. `bloco_4_buscas.js` — buscas sem resultado do site: `POST /b` (público, só o termo, sem IP; tabela `buscas` criada sozinha; até 400 termos novos por dia) e `GET /api/buscas` (aba Procurados do painel, atrás de `protegido`). Rotas: `if (url.pathname === '/b') return buscaRegistrar(req, env);` e `if (url.pathname === '/api/buscas') return protegido(req, env, url, apiBuscas);`. Criado em 07/11/2026.

4. `bloco_5_visitas.js` — visitas reais e funil: `POST /v` (público, aviso do `cliques.js` quando um navegador de verdade abre a página; só dia, origem, tipo de página e se é a 1ª da sessão; tabela `visitas` criada sozinha) e `GET /api/funil` (aba **Funil** do painel: visitas → cliques → pedidos do CSV, só contagens, atrás de `protegido`). Rotas: `if (url.pathname === '/v') return visitaRegistrar(req, env);` e `if (url.pathname === '/api/funil') return protegido(req, env, url, apiFunil);`. Criado em 12/11/2026.

Rotas dentro do `fetch`, logo depois de `const url = new URL(req.url);`:

```js
if (url.pathname === '/api/cliques') return apiCliques(req, env, url);
if (url.pathname === '/api/ganhos') return ganhosApi(req, env, url);
```

Segurança em 3 camadas (`bloco_3_seguranca.js`): chave `REPORT_KEY` + código de 6 dígitos do app autenticador (segredo `TOTP_SECRET`; sem ele o 2º fator fica desligado) + bloqueio de 15 min após 5 erros por IP. No painel, o código vai colado depois da chave no cabeçalho `Authorization`. Rotas: `protegido(req, env, url, apiCliques)`.

Segurança: a chave (`REPORT_KEY`) é um segredo do Worker e vai no cabeçalho `Authorization: Bearer`, nunca na URL. Comissão fica só no D1, nunca neste repositório.

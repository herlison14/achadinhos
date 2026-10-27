# Achadinhos do Binga — guia para o Claude

Dono: Herlison (Instagram @achadinhosdobinga, GitHub herlison14/achadinhos). Responder em português do Brasil; datas em DD/MM/AAAA nas planilhas e textos (os JSON usam AAAA-MM-DD). Ele quer que eu discorde quando fizer sentido, aja sozinho e só pergunte quando estiver bloqueado.

## Arquitetura (detalhes em `dados/LEIAME.md` e `worker/LEIAME.md`)
- **Fonte única:** `dados/itens.json` (+ `historico.json`). Nunca editar `index.html` à mão: ele é gerado por `python3 -I tools/vigia.py build`, que também gera `dados/quedas.json`.
- **Consumidores:** site (`index.html`), painel (`painel/`, lê `../dados/*.json`), Telegram/WhatsApp (`tools/canais.py`), Instagram (`tools/instagram.py`, `dados/posts.json`).
- **Backend:** Cloudflare Worker `cliques-binga` (D1) em `worker/` (blocos colados no painel da Cloudflare à mão; não há deploy automático). `/api/cliques` e `/api/ganhos` ficam atrás de chave (`REPORT_KEY`) + código 2FA (`TOTP_SECRET`) + bloqueio após 5 erros/15 min.
- **Hospedagem:** GitHub Pages + Cloudflare. Workflows em `.github/workflows/` (canal-telegram, fotos, instagram, sincronia).

## Rotina para qualquer mudança de ofertas
1. Editar `dados/itens.json` (e `historico.json` via `vigia.py atualizar` quando for preço).
2. `python3 -I tools/vigia.py build`
3. `python3 -I tools/sincronia.py` — tem que terminar em `SINCRONIA: OK`.
4. `git pull --rebase`, commit, push. O fluxo `sincronia` confere de novo na nuvem.
- Texto de `nome`, `ex`, `pre`, `pos`, `cta` é HTML já escapado (`&amp;`).
- Meta: ~30 ofertas por loja (Shopee 32, Amazon 30, Magalu 30, Mercado Livre 30, AliExpress 28).
- Preço só entra com conferência na loja e data. Nunca inventar preço, desconto, estoque ou avaliação. Itens sem conferência há mais de 30 dias saem da página.

## Links de afiliado
- Amazon: `https://www.amazon.com.br/dp/ASIN?tag=herlisonsanto-20`.
- Mercado Livre: link `meli.la` gerado pelo gerador de links dele (usa o login dele).
- Shopee: conta de afiliado 18306050983. AliExpress e Magalu: gerados nos portais dele.
- Todo conteúdo promocional leva "Publicidade: links de afiliado".

## Segurança (regras firmes)
- Nunca gravar no repositório ou repetir no chat: `REPORT_KEY`, `TOTP_SECRET`, `IG_TOKEN`, `IG_USER_ID`, senhas. Segredos ficam em GitHub Secrets / Cloudflare.
- O repositório é público (decisão do Herlison em 26/10/2026, depois de varredura sem segredos no histórico). `tools/sincronia.py` também varre os arquivos atrás de tokens/senhas e falha se achar; rodar antes de todo push.
- Não digitar login/senha dele em lojas ou portais; pedir que ele entre e seguir daí.
- Não incluir comissões ou ganhos em mensagens do Telegram. A chave de leitura do painel não vai para tarefas agendadas.
- `_headers` tem CSP: fotos de domínios novos precisam entrar em `img-src` (hoje liberados: Amazon `m.media-amazon.com` e ML `http2.mlstatic.com`).

## Armadilhas já encontradas
- Sandbox da nuvem não alcança as lojas nem o github.io: para ler preços/páginas usar o Chrome dele (Claude in Chrome); saída de cada chamada JS é curta (~1000 caracteres), então extrair em linhas compactas.
- Relatórios da Shopee atualizam às 10:30 do dia seguinte; vendas aparecem com um dia de atraso. As outras lojas não têm relatório automático (CSV colado no painel).
- Não usar `pkill -f http.server` no shell (mata a sessão); parar servidores de teste pelo PID.
- Ao mudar preço de item com post agendado no Instagram, ajustar a legenda em `posts.json` (a sincronia avisa).
- Tarefa diária da Shopee depende do computador/Chrome dele ligado; a semanal roda às segundas 19:43.

## Arquivos no computador dele
- Tudo que eu gerar para ele baixar/usar (posts, cards, planilhas, CSV) vai para `Downloads\Achadinhos\` na subpasta certa: `01_Identidade`, `02_Posts_Instagram`, `03_Planilhas_e_Historico`, `04_Site_e_Painel` (via ponte do computador). Nada solto em `Downloads`. Só mover, nunca apagar.

## Campanhas
- 11.11 (11/11/2026) e Black Friday (27/11/2026). Lojas sobem preço antes e "descontam" no dia: por isso registrar o preço real todos os dias antes da data (`vigia.py atualizar`) e só chamar de "menor preço" o que o `historico.json` confirmar. Posts de 08 a 11/11 já estão no calendário como `planejado`.

## Em aberto
- AliExpress em 28 (faltam 2; precisa que ele entre no portal de afiliados).
- Fotos novas de Amazon/ML são hotlink; `fotos.yml` pode baixá-las para o repositório depois.

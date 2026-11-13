# {{nome}} — guia para o Claude

Dono: {{dono}} (Instagram @{{instagram}}, GitHub {{github_usuario}}/{{github_repo}}). Responder em
português do Brasil; datas em DD/MM/AAAA nas planilhas e textos (os JSON usam AAAA-MM-DD).

Esta marca foi criada a partir da estrutura do Achadinhos do Binga, com `tools/nova_marca.py`.
Leia `ESTRUTURA.md` (como o sistema funciona, de forma genérica) e `REPLICAR.md` (o que ainda
falta configurar: contas, segredos, logo, primeiros produtos) antes de operar.

## Arquitetura (detalhes em `dados/LEIAME.md`, `worker/LEIAME.md` e `ESTRUTURA.md`)
- **Fonte única:** `dados/itens.json` (+ `historico.json`). Nunca editar `index.html` à mão: ele é
  gerado por `python3 -I tools/vigia.py build`, que também gera `dados/quedas.json`.
- **Consumidores:** site (`index.html`), painel (`painel/`, lê `../dados/*.json`), Telegram/WhatsApp
  (`tools/canais.py`), Instagram (`tools/instagram.py`, `dados/posts.json`).
- **Backend:** Cloudflare Worker `{{prefixo}}-cliques` (D1) em `worker/` (blocos colados no painel
  da Cloudflare à mão; não há deploy automático). `/api/cliques`, `/api/ganhos` e `/api/funil` ficam
  atrás de chave (`REPORT_KEY`) + código 2FA (`TOTP_SECRET`) + bloqueio após 5 erros/15 min.
- **Hospedagem:** GitHub Pages (ou Cloudflare Pages) + Cloudflare. Workflows em
  `.github/workflows/` (canal-telegram, fotos, instagram, sincronia, métricas, auditoria).

## Autonomia
Ajuste esta seção com as regras que {{dono}} definir (o que pode ser feito sozinho, só comunicando
depois, e o que precisa de aprovação prévia). Limites que devem continuar valendo sempre:
segurança (nada de segredos, senhas, compras, contas), nada de preço inventado, e nada que viole
as regras da Meta (sem seguir/curtir/comentar em massa, sem DM frio, sem isca de engajamento, sem
comprar seguidores).

## Rotina para qualquer mudança de ofertas
1. Editar `dados/itens.json` (e `historico.json` via `vigia.py atualizar` quando for preço).
2. `python3 -I tools/vigia.py build`
3. `python3 -I tools/sincronia.py` — tem que terminar em `SINCRONIA: OK`.
4. `git pull --rebase`, commit, push.
- Preço só entra com conferência na loja e data. Nunca inventar preço, desconto, estoque ou
  avaliação. Itens sem conferência há mais de 30 dias saem da página.

## Links de afiliado
- Amazon: `https://www.amazon.com.br/dp/ASIN?tag={{amazon_tag}}`.
- Mercado Livre: link `meli.la` gerado pelo gerador de links do dono (usa o login dele).
- Shopee: conta de afiliado {{shopee_afiliado}}. AliExpress e Magalu: gerados nos portais do dono.
- Awin: publisher {{awin_publisher}} — formato
  `https://www.awin1.com/cread.php?awinmid=<programa>&awinaffid={{awin_publisher}}&ued=<url codificada>`.
- Todo conteúdo promocional leva "Publicidade: links de afiliado".

## Segurança (regras firmes)
- Nunca gravar no repositório ou repetir no chat: `REPORT_KEY`, `TOTP_SECRET`, `IG_TOKEN`,
  `IG_USER_ID`, senhas. Segredos ficam em GitHub Secrets / Cloudflare.
- Antes de qualquer push, rodar `tools/sincronia.py`: ele varre o repositório atrás de
  tokens/senhas e falha se achar.
- Não digitar login/senha do dono em lojas ou portais; pedir que ele entre e seguir daí.
- Não incluir comissões ou ganhos em mensagens do Telegram. A chave de leitura do painel não vai
  para tarefas agendadas.
- `_headers` tem CSP: fotos de domínios novos precisam entrar em `img-src`.

## Loja nova (quando um afiliado novo for aprovado)
`tools/nova_loja.py` (herdado do Achadinhos) cadastra a loja no site, Instagram e Telegram de uma
vez. Veja o cabeçalho do script para o uso e revise se os ~16 arquivos que ele toca ainda batem com
a estrutura desta marca (alguns nomes podem ter mudado no `nova_marca.py`).

## Armadilhas já encontradas (herdadas do Achadinhos; confirme se ainda se aplicam aqui)
- Sandbox da nuvem pode não alcançar as lojas nem a hospedagem do site: usar o navegador do dono
  para ler preços/páginas.
- Relatórios de venda de algumas lojas (ex.: Shopee) atualizam só no dia seguinte.
- Ao mudar preço de item com post agendado no Instagram, ajustar a legenda em `posts.json`.
- Tarefas que dependem do computador do dono não rodam sem ele ligado/conectado.

## Em aberto
- (Preencha aqui as pendências desta marca conforme forem surgindo, do mesmo jeito que o
  Achadinhos registra as suas.)

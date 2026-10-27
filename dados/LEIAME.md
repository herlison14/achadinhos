# Dados do Achadinhos do Binga

- `itens.json`: as ofertas da página (nome, loja, categoria, link de afiliado, foto, preço, data da última conferência AAAA-MM-DD). **Fonte de verdade**: o `index.html` é gerado a partir daqui.
- `historico.json`: preço de cada oferta por dia (`id -> [[data, preço], ...]`). Não guarda IP nem dados de visitantes.
- `../tools/vigia.py`: ferramenta (Python 3, sem instalar nada).

## Rotina semanal
1. Conferir os preços nas lojas e montar um CSV `id_ou_link;preco;data` (ex.: `a1eb8e1a;18,90;27/10/2026`).
2. `python3 tools/vigia.py atualizar precos.csv` (grava histórico e mostra quedas/altas).
3. `python3 tools/vigia.py build` (regera o `index.html`; itens sem conferência há mais de 30 dias saem da página).
4. `python3 tools/vigia.py relatorio` (quedas recentes e itens sem conferência há mais de 7 dias).
5. Commit e push; a Cloudflare Pages publica.

Para incluir ou remover uma oferta, edite `itens.json` e rode o `build`. O texto de `nome`, `ex`, `pre`, `pos` e `cta` é HTML já escapado (use `&amp;` para `&`).

## Calendário de posts
- `posts.json`: cada post (data, hora, formato, loja, tema, canal, produtos, status). Mostrado na aba "Calendário" do painel (`/painel/`), que cruza com os cliques do dia quando você carrega a aba Cliques.
- Registrar: `python3 -I tools/vigia.py post --data 2026-11-10 --formato carrossel --tema "5 achadinhos" --loja magalu --ids id1,id2 --status planejado`
- Mudar status: `python3 -I tools/vigia.py post-status ID_DO_POST publicado`
- Origem do clique: o link da bio é um só, então a origem é por canal (`?o=ig` bio, `?o=st` stories, `?o=tg` Telegram, `?o=wa` WhatsApp, `?o=bf` Black Friday).

## Publicação automática no Instagram
- `../tools/instagram.py` + `.github/workflows/instagram.yml` publicam sozinhos, pela API oficial, os posts de `posts.json` com `canal: "ig"`, `status: "agendado"` e formato `carrossel` ou `post` na data/hora marcadas (horário de Brasília). Reels continuam manuais.
- Cada post agendado precisa de `imagens` (JPEG 1080x1350 em `postagens/<id>/01.jpg`, ...), `legenda` (texto completo, com "Publicidade: links de afiliado") e `produtos` (ids). Para colocar na fila: `python3 -I tools/vigia.py post-status ID agendado`.
- Travas: preço de cada produto conferido há no máximo 7 dias e escrito na legenda como `R$ 52,82`; atraso de no máximo 6 h; imagens públicas em JPEG; não duplica se o texto já está no perfil. Se algo falha, o post vira `bloqueado` e o Telegram avisa.
- Segredos do GitHub (nunca no repositório): `IG_TOKEN` e `IG_USER_ID`. O token vale 60 dias e é renovado toda segunda pelo fluxo.
- Testar sem publicar: Actions > "Instagram (publicador)" > Run workflow > `testar`.

## Sincronia entre site, painel e canais
- `itens.json` é a fonte única. Painel (`/painel/`), canal do Telegram, textos do WhatsApp e publicador do Instagram leem esses dados na hora de rodar; o site (`index.html`) é gerado por `python3 -I tools/vigia.py build`.
- `python3 -I tools/sincronia.py` confere página x itens.json (links, preços, contador), histórico, quedas, posts e legendas agendadas. Sai com erro se algo estiver fora de sincronia.
- `.github/workflows/sincronia.yml` roda sozinho a cada mudança em `dados/itens.json`/`historico.json` e todo dia às 10:30: regenera e publica a página se necessário e roda a conferência.
- Lojas e metas: ~30 ofertas por loja (Shopee, Amazon, Mercado Livre, Magalu; AliExpress 28). Fotos de Amazon e Mercado Livre novas usam o endereço da própria loja (liberado no `img-src` do `_headers`).
- A conferência também varre o repositório (que é público) atrás de tokens, chaves e senhas escritas em arquivos e falha se achar algo.

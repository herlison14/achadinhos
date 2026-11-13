# Checklist para colocar a marca nova no ar

O `tools/nova_marca.py` só troca texto e zera dados. Estas contas, chaves e arquivos visuais
ninguém cria por você — é o roteiro do que falta, na ordem mais rápida.

## 1. Repositório e hospedagem
- [ ] Criar o repositório no GitHub (nome igual ao `github_repo` do marca.json), público ou
      privado (se público, nunca comitar segredo — o `sincronia.py` varre e falha se achar).
- [ ] `git init`, primeiro commit, push.
- [ ] Ativar GitHub Pages (ou Cloudflare Pages) apontando para a pasta.
- [ ] Comprar/apontar o domínio para a hospedagem escolhida.

## 2. Logo e identidade
- [ ] Trocar `img/marca.webp`, `img/og.jpg`, `img/favicon-32.png`, `img/favicon-192.png`,
      `img/apple-touch-icon.png` pela logo da marca nova.
- [ ] Cores: `index.html` (variáveis CSS `--bg`, `--fg`, `--amarelo`, etc.) e `painel/index.html`.
- [ ] Conferir a linha 2 da logo (texto sob o nome) nos geradores de card
      (`tools/cards.py`, `tools/stories.py`, `tools/reels.py`) — o script já tentou trocar, mas
      vale olhar o resultado visual.

## 3. Contas de afiliado
- [ ] Amazon Associados (tag de afiliado).
- [ ] Awin (publisher ID) — se for usar as lojas da Awin (KaBuM!, Nike, Dafiti, etc.).
- [ ] Shopee (conta de afiliado).
- [ ] Mercado Livre (gerador de links, usa o login do dono).
- [ ] AliExpress e Magalu (portais próprios de afiliado).
- Sem essas contas, não gere link de afiliado — o sistema não confere preço sozinho em loja sem
  link real.

## 4. Instagram e Telegram
- [ ] Criar a conta profissional do Instagram e a Página do Facebook ligada a ela.
- [ ] Criar um app no developers.facebook.com próprio desta marca (nunca reaproveitar o app de
      outra marca) e gerar `IG_TOKEN` + descobrir `IG_USER_ID`.
- [ ] Criar o bot do Telegram no @BotFather (nome e token próprios) e o canal.
- [ ] Segredos no GitHub (Settings > Secrets > Actions): `IG_TOKEN`, `IG_USER_ID`,
      `TELEGRAM_TOKEN`.

## 5. Cloudflare (Workers + D1)
- [ ] Criar o banco D1 (`<prefixo>-cliques` ou nome à sua escolha).
- [ ] Publicar os 3 Workers (`<prefixo>-cliques`, `<prefixo>-bot`, `<prefixo>-agendador`),
      colando os blocos de `worker/` na ordem do `worker/LEIAME.md`.
- [ ] Gerar `REPORT_KEY` (chave do relatório) e `TOTP_SECRET` (segredo do 2FA, base32; qualquer
      app autenticador como Google Authenticator serve para ler o código).
- [ ] Segredos do bot (`worker/bot/LEIAME.md`): `TELEGRAM_TOKEN`, `TG_SECRET`, `META_APP_SECRET`,
      `IG_VERIFY`, `IG_PAGE_TOKEN`.
- [ ] Segredo do agendador (`worker/agendador/LEIAME.md`): `GH_TOKEN` (fine-grained, só deste
      repositório, Actions leitura/gravação).
- [ ] `_headers`: liberar no `img-src` o(s) domínio(s) de foto de cada loja usada.

## 6. Primeiros produtos
- [ ] Conferir manualmente de 15 a 30 produtos por loja (preço, estoque, link de afiliado real).
- [ ] `python3 -I tools/vigia.py atualizar` para gravar no histórico, depois
      `python3 -I tools/vigia.py build`.
- [ ] `python3 -I tools/sincronia.py` — tem que terminar em `SINCRONIA: OK`.
- [ ] Commit e push.

## 7. Teste de ponta a ponta
- [ ] Abrir o site publicado e clicar em um botão de loja: o clique tem que aparecer no
      `/api/cliques` do Worker.
- [ ] Rodar o publicador do Instagram em modo `testar` antes do primeiro post real.
- [ ] Mandar uma mensagem de teste no bot do Telegram.
- [ ] Rodar `tools/sincronia.py` uma última vez.

## O que NÃO copiar da marca original (mesmo sem querer)
Conteúdo é da outra marca: posts, Reels, Stories, fotos de produto, canal de WhatsApp,
listas de afiliado (Mercado Livre), plano de Natal, Storefront da Awin. O `nova_marca.py` já não
copia essas pastas — se faltar algo, copie só o código, nunca o conteúdo.

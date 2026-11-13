# Como esta estrutura funciona (qualquer marca)

Este documento descreve a arquitetura que o Achadinhos do Binga usa, de forma genérica. O
`tools/nova_marca.py` copia e adapta o código; este arquivo explica o que cada peça faz, para
quem for operar (ou ajustar) a marca nova.

## Peças

- **Dados (`dados/itens.json` + `historico.json`): fonte única.** Nada mais se edita à mão.
  `python3 -I tools/vigia.py build` gera o site (`index.html`, `lojas/`, `ofertas/`, `sitemap.xml`)
  a partir daqui. `tools/vigia.py atualizar` grava preço novo no histórico.
- **Site:** estático (GitHub Pages ou Cloudflare Pages). CSS e fontes auto-hospedados (CSP não libera
  Google Fonts). `cliques.js` avisa cliques em loja (`/c`) e visitas reais (`/v`) ao Worker de cliques,
  sem IP nem cookie.
- **Painel (`painel/`):** HTML/JS puro, lê os JSON de `dados/` direto (sem servidor próprio) e os
  endpoints protegidos do Worker (`/api/cliques`, `/api/ganhos`, `/api/buscas`, `/api/funil`). PWA
  instalável (`sw.js`).
- **Canais:**
  - Instagram: `tools/instagram.py` publica pela API oficial (Graph API), com token em GitHub
    Secrets. Precisa de um app Meta próprio (developers.facebook.com) e de uma Página do Facebook
    ligada à conta profissional do Instagram.
  - Telegram: `tools/telegram_post.py` espelha cada post; bot próprio (via @BotFather), token em
    GitHub Secrets.
  - WhatsApp: sem API própria neste modelo; texto pronto (`tools/canais.py`) publicado manualmente
    (ou por automação de navegador) no WhatsApp Web, com limite de envios por dia.
- **Workers (Cloudflare, D1 SQLite), colados à mão no painel da Cloudflare — sem deploy automático:**
  - `<prefixo>-cliques`: contador de cliques e visitas (tabelas `cliques`, `visitas`, `buscas`,
    `ganhos`, `tentativas`). Os blocos ficam em `worker/bloco_*.js`; o `worker/LEIAME.md` explica a
    ordem de colagem e as rotas.
  - `<prefixo>-bot`: responde DM e comentário no Telegram/Instagram com ofertas reais
    (`worker/bot/`).
  - `<prefixo>-agendador`: dispara o publicador do Instagram quando o cron do GitHub atrasa
    (`worker/agendador/`).
  - Segurança: `REPORT_KEY` (chave) + `TOTP_SECRET` (2FA, código de 6 dígitos de app
    autenticador) + bloqueio após 5 erros/15 min (`worker/bloco_3_seguranca.js`).
- **GitHub Actions (`.github/workflows/`):**
  - `sincronia.yml`: regenera o site a cada mudança em `dados/` e roda a conferência
    (`tools/sincronia.py`), que também varre o repositório atrás de segredos vazados.
  - `instagram.yml`: publica os posts agendados (cron a cada 10 min) e renova o token semanalmente.
  - `metricas.yml`: grava métricas do Instagram (`dados/metricas.json`) e roda o analista/tendências.
  - `auditoria.yml`: confere se todos os robôs fizeram o que deveriam (`tools/auditor.py`).
  - `canal-telegram.yml`, `fotos.yml`, `fotos-urls.yml`: apoio.

## Regras que valem para qualquer marca (não são specíficas do Achadinhos)

- Preço, desconto, estoque e avaliação **nunca são inventados** — só o que foi conferido na loja,
  com data. Item sem conferência há mais de 30 dias some do site.
- Nada de segredo (token, senha, chave) no repositório, mesmo que o repositório seja público. Ficam
  em GitHub Secrets e nos segredos do Worker no Cloudflare.
- Nada que viole as regras da Meta: sem seguir/curtir/comentar em massa, sem DM frio, sem isca de
  engajamento, sem comprar seguidor.
- Todo conteúdo promocional leva o aviso de publicidade/links de afiliado.
- A conferência de preço em lojas que bloqueiam o acesso direto do servidor (sandbox na nuvem) é
  feita pelo navegador do dono da marca (Claude in Chrome ou similar), não pelo servidor.

## O que muda de marca para marca

Tudo o que o `tools/nova_marca.py` troca a partir do `marca.json`: nome, domínio, Instagram,
Telegram, usuário/repositório do GitHub, subdomínio dos Workers, tag de afiliado da Amazon, IDs de
publisher da Awin/Shopee. **Contas, segredos, logo, cores e primeiros produtos não são automáticos**
— isso é o dono da marca nova e/ou quem for operar que precisam fazer (veja REPLICAR.md).

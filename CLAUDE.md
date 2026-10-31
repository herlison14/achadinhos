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
- Meta (ampliada em 31/10/2026): crescer em etapas; Amazon 45 e Magalu 43 já feitos (fáceis de conferir em lote pelo Chrome e links montados por mim); Shopee 31, Mercado Livre 30 (2 links com problema: Coleira peitoral e Compressor), AliExpress 28 dependem de links gerados por ele nos portais. Conferir em lote: Amazon e Magalu por fetch no Chrome (same-origin); links ML (meli.la) abrem o perfil social com o produto no topo.
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
- Tudo que eu gerar para ele baixar/usar vai para `Downloads\Achadinhos\` (via ponte do computador), na subpasta certa: `01_Imagens_e_Identidade`, `02_Instagram\{Reels,Stories,Posts_e_Carrosseis}`, `03_Planilhas\{Mestre,Historico_Postados,Listas_por_Loja,Ganhos_CSV}`, `04_Site_e_Painel`, `05_Zips_Originais`, `06_WhatsApp` (cards e textos do canal, uma subpasta por dia). Nada solto em `Downloads`. **Cada canal tem sua própria pasta numerada** (Instagram `02_`, WhatsApp `06_`; Telegram ou outro canal novo ganha `07_`, `08_`...), nunca misturar canais na mesma subpasta (regra do Herlison, 30/10/2026). Só mover, nunca apagar. "History" para ele = Stories. Mapa completo no `LEIAME.txt` da pasta.

## Relatório semanal de vendas
- `python3 -I tools/vendas.py ganhos.csv --dias 7 --saida <arquivo fora do repo>`: lê o CSV do painel (`data;loja;produto;pedidos;comissao`) e lista o que vendeu e o que repetir. Comissão nunca vai para o repositório nem para o Telegram (o script recusa gravar dentro do repo). Eu não tenho a chave do Worker: ele me passa o CSV (Shopee: relatório de vendas exportado).
- Painel agora é PWA (`painel/sw.js`); o Telegram é espelhado pelo `tools/telegram_post.py` depois de cada post do Instagram.

## Visibilidade (Google e Pinterest)
- Search Console verificado em 31/10/2026 (tag `google-site-verification` no `<head>` do `index.html`; não remover). Sitemap enviado e indexação da home solicitada.
- O `vigia.py build` também gera o JSON-LD (schema.org: ItemList de Product com preço conferido e link) entre `<!--ld-inicio-->` e `<!--ld-fim-->` no `<head>`; não apagar os marcadores.
- `vigia.py build` também gera `ofertas/<categoria>/` e `lojas/<loja>/` (módulo `tools/paginas.py`, só dados reais de `itens.json`/`historico.json`), regrava o `sitemap.xml` e preenche o bloco `<!--paginas-inicio-->` do rodapé da home com links para elas. Não editar essas pastas à mão e não apagar os marcadores.
- Agendador: `worker/agendador/` (Worker `agendador-binga`, cron da Cloudflare a cada 10 min) dispara o `instagram.yml` quando há post `agendado` vencido, porque o cron do GitHub atrasa horas (31/10/2026: 3 h). No ar desde 31/10/2026 (cron de 10 em 10 min confirmado: log "nada no horário"). Usa o segredo `GH_TOKEN` (tipo Segredo; token fine-grained só do repo, Actions leitura/gravação, vence em 31/10/2027) criado pelo Herlison. 31/10/2026: o Worker NÃO disparou nos posts de 12:30 e 16:00 (nenhuma execução do workflow até 16:13); publiquei à mão com acao=publicar. Causa ainda desconhecida: ler Cloudflare > agendador-binga > Observabilidade > Eventos (procurar "GitHub recusou o disparo" ou "nada no horário") e conferir as permissões do GH_TOKEN. Enquanto isso, conferir cada post e disparar à mão.; se aparecer "GitHub recusou o disparo: HTTP 401/403" nos registros do Worker, o token está errado ou sem permissão. Se falhar, disparo `acao=publicar` à mão.
- Pinterest: `FONTES=/tmp/f python3 -I tools/pinterest.py` gera `pinterest/<id>.jpg` (sem preço na imagem) e `pinterest/pins.csv` (envio em massa; Media URL aponta para o raw do GitHub, só vale depois do push). Conta/quadros são do Herlison (não crio conta). Pasta no PC: `08_Pinterest` (`07_` reservada ao Telegram).

## Campanhas
- 11.11 (11/11/2026) e Black Friday (27/11/2026). Lojas sobem preço antes e "descontam" no dia: por isso registrar o preço real todos os dias antes da data (`vigia.py atualizar`) e só chamar de "menor preço" o que o `historico.json` confirmar. Posts de 08 a 11/11 já estão no calendário como `planejado`.

## Em aberto
- **Instagram automático (resolvido em 31/10/2026):** o app Meta "Achadinhos Publicador" usa o login unificado, então o token é do Facebook (`EAA...`) e não do login do Instagram (`IGAA`). `tools/instagram.py` detecta o `EAA`, usa `graph.facebook.com`, acha a conta pela Página do Facebook ligada (`/me/accounts`) e publica com o token da Página. Segredos em GitHub Secrets: `IG_TOKEN` (token EAA estendido; o `IG_USER_ID` é descoberto sozinho) — nunca no chat, eu não digito token. Se parar de publicar: Actions > Instagram (publicador) > `status` (`gh api -X POST repos/herlison14/achadinhos/actions/workflows/instagram.yml/dispatches -f ref=main -f 'inputs[acao]=status'`) e ler as anotações da execução (`gh api repos/herlison14/achadinhos/check-runs/<job>/annotations`): mostram tipo/tamanho do token, validade, permissões e motivo da recusa. Código de saída 3 = faltam chaves, 1 = token recusado. Se o token for recusado, o robô não mexe na fila (posts ficam `agendado` e saem até 6 h depois do horário); refazer o token: Explorador da Graph API (app Achadinhos Publicador; permissões pages_show_list, instagram_basic, instagram_content_publish, ads_read; escolher a Página e a conta) e estender em developers.facebook.com/tools/debug/accesstoken. Plano B: publicar pelo Chrome dele (aba do Instagram logada, `file_upload` com arquivos de `postagens/<id>/`) e marcar `publicado` em `posts.json`.
- Fila de 31/10 e 01/11 (agendado, 09:00 / 12:30 / 16:00 / 19:30 BRT): moda-shopee, cozinha-mista, beleza-shopee, casa-shopee (31/10); amazon-66-96, despensa-shopee (11-19), despensa-shopee (11-23), natal-shopee (01/11). Já publicados em 30/10: shopee-ate20 e beleza-shopee (pelo Chrome).
- WhatsApp: kit de 30/10 em `Downloads\Achadinhos\06_WhatsApp\whatsapp_30-10-2026`; ainda não atuamos no canal (o Herlison pediu para começar depois dos posts do Instagram).
- AliExpress em 28 (faltam 2; precisa que ele entre no portal de afiliados).
- Fotos novas de Amazon/ML são hotlink; `fotos.yml` pode baixá-las para o repositório depois.

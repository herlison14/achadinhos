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
- Meta (ampliada em 31/10/2026): crescer em etapas; Amazon 45 e Magalu 43 já feitos (fáceis de conferir em lote pelo Chrome e links montados por mim); Shopee 31, Mercado Livre 40 (links gerados no gerador dele, linkbuilder do ML, em lote, 1 URL por linha; 2 links ruins refeitos em 31/10), AliExpress 28 dependem de links gerados por ele nos portais. Conferir em lote: Amazon e Magalu por fetch no Chrome (same-origin); links ML (meli.la) abrem o perfil social com o produto no topo.
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
- Tarefa diária "Relatório diário Shopee e preços" (11:07, exige o computador dele): desde 02/11/2026 a conferência de preços (até 25 itens/dia) prioriza itens de posts agendados/planejados dos próximos 3 dias, depois os mais antigos; corrige legendas e cards de posts de produto afetados. Sem o Chrome dele ligado, nada é reconferido: o robô do Instagram bloqueia post cujo item passou de 7 dias ou cujo preço da legenda mudou.

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

## Rotina de crescimento (adicional, criada em 02/11/2026)
- Pedido do Herlison: posts que tragam mais gente (visita ao site, salvar, enviar, comentar), **além** da rotina de posts de produtos, que **não se mexe** (calendário, horários e posts já programados ficam como estão).
- Fonte: `dados/crescimento.json` (lista de posts com slides e legenda). `python3 -I tools/crescimento.py` (`--refazer` só redesenha os cards) gera `postagens/<id>/NN.jpg` (1080x1350, **sem preço**) e registra em `dados/posts.json` com `"produtos": []`, `"sem_preco": true`, `"objetivo"`, status `agendado`. Fontes: converte sozinho de `fonts/*.woff2` (precisa de `pip install fonttools brotli`).
- O robô (`tools/instagram.py`) e o espelho do Telegram (`tools/telegram_post.py`) aceitam `sem_preco`: sem trava de produto/preço, mas a legenda não pode ter "R$" e leva "Publicidade: links de afiliado".
- Horários próprios, para não colidir com os de produto (08:00, 09:00, 12:00, 12:30, 16:00, 19:00, 19:30): **10:30, 14:30, 17:30, 21:00**. Meta: 1 por dia; alternar objetivo (visita, salvar, enviar, comentar).
- Conteúdo só com fatos verdadeiros do site/processo (busca, seção "Caiu de preço", preço com data de conferência, categorias e lojas) e dicas gerais de compra. Nada de preço, desconto, sorteio, "curta se", "marque 3": a Meta reduz o alcance de isca de engajamento (a ferramenta recusa essas frases).
- Tarefa agendada semanal (domingo): escreve os posts dos próximos 7 dias em `crescimento.json` (sem repetir tema), roda a ferramenta, `sincronia.py`, `git pull --rebase`, commit e push. Pode rodar na nuvem sem o Chrome dele, porque não tem preço.
- Posts de 03 a 08/11/2026 já criados (site-tudo-num-lugar, qual-loja, 4-jeitos-preco-bom, lista-11-11-black-friday, como-usar-o-site, o-que-voce-quer-ver).

- Métricas (03/11/2026): `python3 tools/instagram.py metricas` (fluxo `.github/workflows/metricas.yml`, todo dia 22:30, só leitura) lista curtidas e comentários por post publicado e, se o token tiver `instagram_manage_insights`, alcance, salvamentos, envios e views. Resultado fica no resumo da execução (log público do Actions: só números, sem segredo) e no artefato `metricas-instagram`. Em 03/11: 21 seguidores, posts recentes com 0 curtidas/0 comentários; token ainda SEM `instagram_manage_insights` (precisa refazer o token no Explorador da Graph API com essa permissão).
- Reels publicados pelo robô (02/11/2026): `tools/instagram.py` aceita `formato: reel` com `"video": "postagens/<id>/reel.mp4"` (upload resumível em rupload.facebook.com; se falhar, tenta `video_url` do raw do GitHub; sai também no feed). Primeiro Reel (queda-do-dia) publicado em 02/11 23:05 (`ig_id` gravado). O espelho do Telegram ainda ignora Reels (só posta o que tem `imagens`).
- **Natal 2026** (02/11/2026): plano em `dados/natal/PLANO.md`. 10 Reels de Natal sem preço já agendados (17/11 a 20/12, 20:00) em `dados/reels.json`; o que falta é catálogo de ~30 produtos por loja (precisa do Chrome dele e dos links gerados por ele) e carrosséis/Reels de produto com preço conferido. Tudo de Natal só depois do 11.11.
- Reels temáticos (11.11/Black Friday, sem preço): fonte `dados/reels.json`; `python3 -I tools/reels_tema.py` gera `postagens/<id>/reel.mp4` + `capa.jpg` (1080x1920, 30 fps, ~16 s, trilha original sintetizada em `tools/reel_audio.py`) e registra em `posts.json` como `agendado` (`sem_preco`). Meta: **5 por semana**, às 20:00 (slot próprio). Legenda com "Gostou? Curte, salva e manda pra quem vai comprar" + "Publicidade: links de afiliado"; o validador recusa R$, %, "curta se", "marque N", sorteio, "ganhe", "grátis", "desconto". Semana 03 a 08/11 criada (faltam-8-dias, 3-cuidados-black-friday, black-friday-21-dias, 11-11-no-dia, faltam-3-dias). Reel "Caiu de preço" (`tools/reels.py`, dados reais, só com itens conferidos há ≤7 dias) entra quando houver quedas com foto.
- Reels (03/11/2026): `python3 -I tools/reels.py` gera `postagens/<id>/reel.mp4` (1080x1920, ~20 s, sem áudio, ffmpeg) do tipo "Caiu de preço" só com quedas reais de `quedas.json` (itens com foto local, conferidos há no máximo 7 dias) e registra o post como `planejado` (formato `reel`). O robô ainda NÃO publica Reels; falta o caminho `media_type=REELS` no `instagram.py` e um teste real aprovado pelo Herlison.

- **Robô de respostas (04/11/2026 em diante):** `worker/bot/` (Worker `bot-binga`, colado à mão no painel da Cloudflare). Responde DM no Telegram (webhook `/telegram`) e no Instagram (webhook `/instagram`) com ofertas reais do `itens.json` (preço só se conferido ≤ 7 dias, com data). Passo a passo e segredos em `worker/bot/LEIAME.md`. Instagram depende de token com `instagram_manage_messages` e de Revisão do App para o público.

- **Vitrines (03/11/2026):** Mercado Livre: listas de afiliado no perfil social (API interna `wishlist/elements/override`; limite de 2 listas de afiliado; "Natal 2026 Achadinhos" com 30 itens, PÚBLICA, link `https://meli.la/2XzAJCX` em `dados/natal/listas.json` → botão em `ofertas/natal/`; "Minhas recomendações" com 59 itens (24 antigos sem ligação com o site + os nossos 40), PÚBLICA desde 03/11/2026, link `https://meli.la/2g9CabF` em `dados/natal/listas.json` chave `meli_geral` → botão em `lojas/meli/`). Magalu: loja do Influenciador Magalu (`in_400408`) sem coleções. Amazon: inscrição no Amazon Influencers recusada em 03/11/2026 (poucos seguidores; tentar de novo com mais audiência); sem Listas de Ideias no portal BR. Shopee e AliExpress: sem vitrine para afiliado. Página `ofertas/natal/` gerada por `tools/paginas.py` a partir de `dados/natal/ids.json`.

- **Vitrines junto com o site (regra de 03/11/2026):** tudo que muda em produto, site ou Instagram vale também para as lojas. Site (`lojas/`, `ofertas/`) é gerado pelo build; listas do ML são atualizadas pela Parte 3 da tarefa diária (Chrome dele), conforme `dados/natal/LEIAME.md`. Itens removidos não saem da lista sozinhos (avisa).

## Campanhas
- 11.11 (11/11/2026) e Black Friday (27/11/2026). Lojas sobem preço antes e "descontam" no dia: por isso registrar o preço real todos os dias antes da data (`vigia.py atualizar`) e só chamar de "menor preço" o que o `historico.json` confirmar. Posts de 08 a 11/11 já estão no calendário como `planejado`.

## Em aberto
- **Instagram automático (resolvido em 31/10/2026):** o app Meta "Achadinhos Publicador" usa o login unificado, então o token é do Facebook (`EAA...`) e não do login do Instagram (`IGAA`). `tools/instagram.py` detecta o `EAA`, usa `graph.facebook.com`, acha a conta pela Página do Facebook ligada (`/me/accounts`) e publica com o token da Página. Segredos em GitHub Secrets: `IG_TOKEN` (token EAA estendido; o `IG_USER_ID` é descoberto sozinho) — nunca no chat, eu não digito token. Se parar de publicar: Actions > Instagram (publicador) > `status` (`gh api -X POST repos/herlison14/achadinhos/actions/workflows/instagram.yml/dispatches -f ref=main -f 'inputs[acao]=status'`) e ler as anotações da execução (`gh api repos/herlison14/achadinhos/check-runs/<job>/annotations`): mostram tipo/tamanho do token, validade, permissões e motivo da recusa. Código de saída 3 = faltam chaves, 1 = token recusado. Se o token for recusado, o robô não mexe na fila (posts ficam `agendado` e saem até 6 h depois do horário); refazer o token: Explorador da Graph API (app Achadinhos Publicador; permissões pages_show_list, instagram_basic, instagram_content_publish, ads_read; escolher a Página e a conta) e estender em developers.facebook.com/tools/debug/accesstoken. Plano B: publicar pelo Chrome dele (aba do Instagram logada, `file_upload` com arquivos de `postagens/<id>/`) e marcar `publicado` em `posts.json`.
- Fila de 31/10 e 01/11 (agendado, 09:00 / 12:30 / 16:00 / 19:30 BRT): moda-shopee, cozinha-mista, beleza-shopee, casa-shopee (31/10); amazon-66-96, despensa-shopee (11-19), despensa-shopee (11-23), natal-shopee (01/11). Já publicados em 30/10: shopee-ate20 e beleza-shopee (pelo Chrome).
- WhatsApp: kit de 30/10 em `Downloads\Achadinhos\06_WhatsApp\whatsapp_30-10-2026`; ainda não atuamos no canal (o Herlison pediu para começar depois dos posts do Instagram).
- AliExpress em 28 (faltam 2; precisa que ele entre no portal de afiliados).
- Fotos novas de Amazon/ML são hotlink; `fotos.yml` pode baixá-las para o repositório depois.

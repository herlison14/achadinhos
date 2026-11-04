# Worker `bot-binga` (respostas automáticas no Telegram e no Instagram)

Responde mensagem direta com até 3 ofertas de `dados/itens.json` (lido do GitHub, cache de 10 min), no máximo 1 por loja nas primeiras posições.
Regras embutidas: preço só se conferido há ≤ 7 dias (com a data); item com mais de 30 dias sem conferência não aparece; sem desconto/estoque/avaliação inventados; toda resposta tem "Publicidade: links de afiliado"; sem comissão; não guarda mensagens (só dedup e limite de 8 respostas/min por pessoa, em memória). "parar" encerra.
Teste local: `node` importando `worker.js` e chamando `responder("air fryer", itens)`.

## Publicar (colado à mão no painel da Cloudflare, como os outros)
1. Cloudflare > Workers e Pages > Criar > "Hello World" com o nome `bot-binga` > Implantar > Editar código: cole `worker.js` inteiro > Implantar.
2. Configurações > Variáveis e segredos (tipo **Segredo**): `TELEGRAM_TOKEN`, `TG_SECRET` (frase longa inventada por você), `META_APP_SECRET`, `IG_VERIFY` (outra frase inventada), `IG_PAGE_TOKEN`. Nada disso vai para o repositório nem para o chat.

## Telegram (5 minutos)
Abra no navegador (troque os dois valores pelos seus; a página mostra `"ok":true`):
`https://api.telegram.org/bot<TELEGRAM_TOKEN>/setWebhook?url=https://bot-binga.<seu-subdominio>.workers.dev/telegram&secret_token=<TG_SECRET>`
Teste: mande "air fryer" para o bot. Os posts do canal continuam funcionando (enviar mensagem não depende do webhook).

## Instagram (depende da Meta)
1. Refazer o token no Explorador da Graph API com `pages_messaging` e `instagram_manage_messages` (além das atuais), escolher a Página, estender o token e usar o token da PÁGINA em `IG_PAGE_TOKEN`.
2. developers.facebook.com > app "Achadinhos Publicador" > Webhooks > Instagram: URL `https://bot-binga.<subdominio>.workers.dev/instagram`, token de verificação = `IG_VERIFY`, assinar o campo `messages`. `META_APP_SECRET` = chave secreta do app (Configurações > Básico).
3. Em modo Desenvolvimento só responde a contas com função no app (você e testadores); para qualquer pessoa precisa de Revisão do App (`instagram_manage_messages`, acesso avançado). Também: a Meta só permite responder em até 24 h após a mensagem da pessoa.
4. No Instagram: Configurações > Mensagens > "Permitir acesso às mensagens" para ferramentas conectadas.

## Comentários nos posts (comentário → DM e resposta pública)
- Webhook do Instagram: assinar também o campo `comments` (além de `messages`). O token da Página (`IG_PAGE_TOKEN`) precisa de `instagram_manage_comments` (além de `instagram_manage_messages` e `pages_messaging`).
- Quem comenta pedindo link (quero, link, preço, onde compra, manda...) recebe no direct as ofertas DAQUELE post (`dados/posts.json`: `ig_id` → `produtos`), com preço só se conferido há ≤ 7 dias e a data, e a resposta pública "Te mandei no direct". A resposta privada pelo comentário é o caminho oficial da Meta (1 por comentário, até 7 dias depois).
- Outros comentários recebem uma resposta pública curta e variada (máx. 30 por hora). Não responde: a si mesmo, resposta dentro de comentário, só emoji, link/@ de terceiros, reclamação/golpe/fake (vai para o log "comentário para revisão humana" para você ver).
- Só funciona para qualquer pessoa depois da Revisão do App (`instagram_manage_comments` e `instagram_manage_messages`); em modo Desenvolvimento, só para contas com função no app.
- Depois de ligado, os posts podem pedir "comenta QUERO que eu mando o link no direct" (hoje NÃO pedem, porque o robô ainda não está no ar).

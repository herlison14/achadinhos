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

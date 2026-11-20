# Reels com vídeo do Flow — roteiros e prompts (04/11/2026)

Objetivo: 3 Reels de teste para o 11.11, às **20:00** em **09/11, 10/11 e 11/11/2026** (dias sem Reel hoje).
Meta da semana: comparar alcance/salvamentos/envios com os Reels em cards (`dados/metricas.json`).

## Regras para gerar no Flow (plano gratuito)
- Formato **vertical 9:16**, o clipe mais longo que o plano permitir (idealmente 8 s). Se o plano só der clipes curtos, gere mais clipes do mesmo prompt e escolha os melhores.
- **Sem texto na imagem** (a IA erra letras; eu coloco todo o texto depois), **sem logos, sem nomes de lojas ou marcas, sem preço nem números de preço, sem rosto de gente reconhecível** (só mãos, silhuetas, objetos).
- Nada de produto real aparecendo como se fosse o vendido: só cenas genéricas (celular, calendário, sacolas, caixas de presente).
- Salve cada clipe como `flow_<reel>_<n>.mp4` em `Downloads\Achadinhos\02_Instagram\Reels\flow\` e me avise. Gere 2 variações por prompt se o plano deixar; eu escolho.
- Se o Flow mostrar o rótulo/marca d'água de IA, pode deixar; eu marco o Reel como conteúdo de IA ao publicar.

---

## Reel 1 — 09/11 20:00 — "As lojas sobem o preço antes do 11.11" (conferir antes de comprar)
Tom: alerta amigável, sem pânico, sem prometer desconto.

**Clipe 1A (gancho)**
```
Vertical 9:16 cinematic close-up of a hand holding a smartphone in a cozy modern living room at night, warm lamp light, the phone screen shows a generic blurred shopping app with colorful product thumbnails (no readable text, no logos), slow push-in, shallow depth of field, soft ambient sound.
```
**Clipe 1B (lupa)**
```
Vertical 9:16 macro shot of a magnifying glass moving slowly over a blank white paper receipt on a wooden desk, warm side light, soft focus background, no text or numbers visible, calm and curious mood.
```
**Clipe 1C (fechamento)**
```
Vertical 9:16 two hands comparing two smartphones side by side over a table, screens glowing with blurred generic product grids (no readable text, no logos), gentle camera drift, clean bright kitchen background.
```
Texto que eu coloco por cima (não precisa pedir ao Flow): "Antes do 11.11, confere o histórico" / "Loja sobe o preço e 'desconta' no dia" / "No site, o preço vem com a data da conferência".

---

## Reel 2 — 10/11 20:00 — "Amanhã é 11.11: checklist de 3 passos"
Tom: lista salvável (salvar/enviar), contagem regressiva calculada.

**Clipe 2A (calendário)**
```
Vertical 9:16 close-up of a desk calendar page being turned slowly by a hand, warm morning light, soft focus, paper texture, no readable numbers or text, gentle camera push-in.
```
**Clipe 2B (lista)**
```
Vertical 9:16 overhead shot of a hand writing a checklist with check marks in a notebook next to a coffee cup and a smartphone, warm light, handwriting is abstract and illegible (no readable words), calm productivity mood.
```
**Clipe 2C (sacolas)**
```
Vertical 9:16 gentle slow-motion of colorful generic paper shopping bags and gift boxes arranged on a bright table, soft confetti-free daylight, no logos, no text, shallow depth of field.
```
Texto por cima: "Falta 1 dia" / "1. Salva a lista do que você quer" / "2. Compara a loja certa" / "3. Confere o preço no dia" / "Link na bio".

---

## Reel 3 — 11/11 20:00 — "Chegou o 11.11: como comprar com calma"
Tom: dia da data; sem prometer preço baixo, sem urgência falsa.

**Clipe 3A (abertura)**
```
Vertical 9:16 warm sunrise light flooding a living room window, a hand placing a smartphone on a coffee table next to a notebook, calm festive mood, soft focus, no text, no logos.
```
**Clipe 3B (carrinho)**
```
Vertical 9:16 close-up of fingers tapping a smartphone screen showing a blurred generic shopping cart interface with product thumbnails (no readable text, no logos), soft bokeh lights behind, slow dolly-in.
```
**Clipe 3C (pacote)**
```
Vertical 9:16 a delivery box with a simple ribbon being gently placed on a doorstep by a hand, warm evening light, no logos, no text, cozy neighborhood background.
```
Texto por cima: "11.11 chegou" / "Respira: compara antes de comprar" / "Preço com data de conferência no site" / "Link na bio".

---

## Legendas (rascunho; eu valido nas regras da ferramenta)
Todas terminam com: "Gostou? Curte, salva e manda pra quem vai comprar. Link na bio 🔗" + "Os preços podem mudar: confirme na loja antes de comprar." + "Publicidade: links de afiliado." e no máximo 8 hashtags. Sem R$, sem percentual, sem "desconto", "grátis", "ganhe", "imperdível".

## Montagem (eu faço quando os clipes chegarem)
`ffmpeg`: recorte 1080x1920, 3 clipes de ~5 s, texto da marca por cima (fontes de `fonts/`), trilha original de `tools/reel_audio.py`, saída `postagens/<id>/reel.mp4` + `capa.jpg`, registro em `dados/posts.json` como `agendado`, `sem_preco: true`, marcação de conteúdo de IA na descrição interna. Depois `instagram.py testar` e `sincronia.py`.

---

## Padrão REALISTA (a partir de 06/11/2026) — usar sempre

Base que vai em todo pedido ao agente do Flow (Veo 3.1 Lite, 9:16, 8 s, 10 créditos cada; aprovar uma vez):
> Estilo FOTORREALISTA, como filmado num iPhone de verdade: luz natural, câmera na mão com leve tremor, profundidade de campo rasa, texturas reais de pele, tecido e papel, cores naturais, nada de visual 3D ou desenho. Paleta da cena com roxo e amarelo (sacolas, caixas, almofadas). SEM nenhum texto, letra, logo, marca ou número; telas de celular desfocadas; sem rostos (só mãos e corpo).

**Marca:** a IA nunca escreve a marca. Logo (`tools/logo.png`) e o nome "ACHADINHOS DO BINGA" entram SEMPRE na montagem com ffmpeg: gancho no topo, pílula com logo + nome no rodapé e cartão final com logo, nome, "Link na bio", "Publicidade: links de afiliado" e "Vídeo gerado com IA". Assim o nome sai sempre certo.

### Lote 06/11 (gerados)
- 4 entrega (caixas na porta) e 5 relógio — estilo antigo (mais "3D").
- 6 unboxing: mãos de uma mulher abrem uma caixa de papel roxa lisa sobre um sofá cinza, tiram um embrulho amarelo, luz da janela de manhã.
- 7 comparar: mãos seguram o celular na bancada da cozinha ao lado de uma xícara de café, rolam a tela devagar e anotam num bloquinho amarelo.
- 8 entrega real: na porta de um apartamento, mãos recebem uma caixa de papel roxa lisa (só braços, sem uniforme de marca), fim de tarde.

### Próximos (após renovar créditos às 23:27)
- 9 lista da Black Friday: à noite, sala com luzinhas amarelas, mãos escrevem uma lista num caderno roxo no colo, celular ao lado com tela desfocada.
- 10 sacolas na cama: sacolas de papel roxas e amarelas lisas sobre uma cama clara, mão pega uma delas, luz da manhã, câmera aproxima devagar.

---

## Lote mascote 3D — Black Friday + Natal, 15s cada, voz de criança (pedido do Herlison, 20/11/2026)

Pipeline: igual ao de 15/11/2026 (`dados/mascote/LEIAME.md`) — aba **Personagens** do projeto Flow,
digitar `@Bingu` no prompt (nunca descrever o personagem do zero), modelo **Veo 3.1 Lite**, 8s/cena,
aprovar 1x por geração (nunca "Sempre aprovar"). 2 cenas por vídeo (~16s, arredonda pra "15s").
Estilo 3D expressivo (não o fotorrealista dos outros Reels) — igual às cenas já testadas em 15/11.
Áudio nativo do Veo: pedir explicitamente **voz de criança, aguda e animada** pro Binguinho falar a
fala entre aspas. Ressalva já registrada: português não está na lista oficial de idiomas de fala do
Veo 3.1 — confirmar com o Herlison se a narração saiu inteligível depois de baixar.
Nada de preço, número, texto, logo ou nome de loja dentro da cena (entra depois via ffmpeg, igual
aos outros Reels do mascote).

### Vídeo BF-1 — "Contagem regressiva" (Black Friday 27/11/2026, faltam 7 dias)
**Cena 1A:** `@Bingu pulando de alegria, segurando um calendário com uma página voando, fundo roxo
escuro brilhante com confete dourado flutuando ao redor, expressão animada e surpresa. @Bingu fala
com voz de criança, aguda e animada, em português: "Gente, a Black Friday já tá quase chegando!"`
**Cena 1B:** `@Bingu com os dois polegares para cima, sacolas de compras genéricas lisas (roxas e
amarelas, sem logo nenhum) flutuando ao redor, fundo roxo escuro com brilho. @Bingu fala com voz de
criança, aguda e animada, em português: "Eu vou ficar de olho nos preços pra vocês, corre lá no
link da bio!"`

### Vídeo BF-2 — "Corre, mas confere"
**Cena 2A:** `@Bingu correndo animado de um lado da cena, sacolas e caixas de presente lisas (sem
logo) voando ao redor, fundo roxo escuro com brilho dourado, expressão de empolgação. @Bingu fala
com voz de criança, aguda e animada, em português: "Corre, corre, a Black Friday chegou!"`
**Cena 2B:** `@Bingu freando de repente, segurando uma lupa grande e olhando para uma etiqueta de
preço em branco (sem nenhum número ou texto), expressão de atenção e cuidado, fundo roxo escuro.
@Bingu fala com voz de criança, aguda e animada, em português: "Mas antes de comprar, espia se o
preço é de verdade, hein!"`

### Vídeo Natal-1 — "O Natal tá chegando"
**Cena 3A:** `@Bingu usando um gorro de Papai Noel vermelho e branco, fundo roxo escuro decorado com
luzes de Natal roxas e douradas penduradas e neve estilizada leve caindo, expressão alegre e doce.
@Bingu fala com voz de criança, doce e animada, em português: "Ho ho ho, o Natal tá chegando!"`
**Cena 3B:** `@Bingu embrulhando um presente com papel liso dourado e laço roxo, fundo com as mesmas
luzes de Natal, expressão concentrada e feliz. @Bingu fala com voz de criança, doce e animada, em
português: "Eu já separei uma surpresinha de oferta pra você, corre lá no link da bio!"`

### Vídeo Natal-2 — "Presente surpresa"
**Cena 4A:** `@Bingu sacudindo uma caixa de presente grande e lisa (dourada com laço roxo) perto do
ouvido, curioso, fundo roxo escuro com uma árvore de Natal estilizada ao fundo (bolas roxas e
douradas, sem estrela com texto). @Bingu fala com voz de criança, curiosa e animada, em português:
"Será que tem uma surpresa boa aqui dentro?"`
**Cena 4B:** `@Bingu abrindo a caixa, luz brilhante dourada saindo de dentro, expressão de surpresa e
alegria, confete dourado caindo ao redor. @Bingu fala com voz de criança, animada e feliz, em
português: "Oba! Essa aqui é pra você, feliz Natal!"`

### Montagem (quando os 8 clipes chegarem)
Igual ao Reel `2026-11-18-reel-mascote-linknabio`: concatenar as 2 cenas de cada vídeo (fade curto
entre elas, `setsar=1` antes do concat pra evitar erro de SAR), pílula de marca no rodapé (overlay
fixo), cartão final (logo, "ACHADINHOS DO BINGA", "Link na bio", "Publicidade: links de afiliado",
"Vídeo gerado com IA"), 1 trilha contínua de `tools/reel_audio.py` só se a narração não sair boa (se
sair boa, deixar só o áudio nativo do Veo, sem trilha por cima pra não embolar a fala). Registrar em
`dados/posts.json` como `formato: "reel"`, `sem_preco: true`, 1 por dia em horários livres de Reel
(ver `tools/reels_tema.py`, meta de 5/semana, slot 20:00 — escolher outros horários livres pra não
empilhar 4 no mesmo dia).

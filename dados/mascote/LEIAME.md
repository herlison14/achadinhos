# Binguinho — ficha do mascote (15/11/2026)

Mascote 3D do Achadinhos do Binga: a sacola-logo da marca ganhou corpo, rosto e personalidade.
Gerado por IA (nenhum personagem de terceiro); nome dado pelo Herlison: **Binguinho**.

## Imagens de referência (usar sempre, em qualquer ferramenta nova)
- `binguinho_referencia.jpg` (716x1284) — pose neutra, de frente, braços relaxados. **Referência
  principal de identidade** (rosto, cores, proporções).
- `binguinho_comemorando.jpg` (720x1280) — pose animada (comemorando, confete). Referência
  secundária de expressão/pose.

Por que salvar as imagens e não só o nome: qualquer ferramenta de geração de vídeo/imagem nova
(Kairogen, Google Flow/Veo, outra que surgir) recria o personagem do zero a cada prompt se não
receber uma imagem de referência — sem isso o "Binguinho" sai com cara, cor ou proporção diferente
a cada vídeo, o que quebra a identidade visual da marca. Regra: **todo vídeo novo com o mascote
tem que partir de uma destas imagens como referência** (first_frame_url no Kairogen; Ingredients
to Video no Flow/Veo — ver seção abaixo), nunca só do nome ou de uma descrição em texto.

## Ficha visual (descrição completa, para prompt de texto quando a ferramenta não aceitar imagem)
- **Forma do corpo:** sacola de compras amarela, formato retangular (mais larga em cima, levemente
  mais estreita embaixo), em pé, sem base/sombra extra — o próprio corpo é a sacola.
- **Alça:** duas alças roxas (tom roxo escuro/violeta, o roxo da marca) saindo do topo da sacola,
  curvadas, como se fossem "orelhas" ou um arco por cima da cabeça.
- **Rosto:** desenhado direto no corpo da sacola (não é uma cabeça separada). Dois olhos grandes e
  redondos, expressivos (abertos e brilhantes em poses de surpresa/alegria; semicerrados em sorriso
  tranquilo), sobrancelhas finas arqueadas, bochechas rosadas/coradas (blush) dos dois lados, boca
  sorridente (sorriso aberto mostrando "dentes" brancos em poses animadas; sorriso fechado e sutil
  em pose neutra).
- **Marca no peito:** o logo da marca — um "b" roxo minúsculo, estilizado — estampado no centro da
  sacola, abaixo do rosto.
- **Braços e mãos:** braços curtos e grossos, da mesma cor amarela do corpo, saindo das laterais;
  mãos arredondadas (sem dedos individuais detalhados, só o polegar às vezes marcado). Poses usadas
  até aqui: acenando (uma mão levantada), os dois polegares para cima (comemorando), uma mão na
  cintura (pose neutra).
- **Pernas e pés:** pernas curtas e grossas, mesma cor amarela, terminando em "pés" arredondados
  (sem sapato, só a continuação da sacola).
- **Paleta de cores:** amarelo (corpo, #FFC93B aproximado — o amarelo da marca), roxo escuro (alça e
  o "b" do logo, #291258/#5B4B8A aproximado — o roxo da marca), rosa/vermelho suave (bochechas),
  branco (brilho dos olhos, dentes do sorriso).
- **Fundo típico dos vídeos já gerados:** roxo escuro liso ou com brilho/partículas (confete,
  estrelas, corações) flutuando ao redor — combina com a identidade visual do site/Instagram
  (fundo roxo dos Reels "Caiu de preço", `tools/reels.py`).
- **O que NUNCA muda:** é sempre a MESMA sacola-personagem — não trocar por outro bicho, objeto ou
  estilo de desenho (ex.: não virar um boneco humano, não virar outro tipo de sacola/caixa, não
  mudar a cor base pra outra que não seja o amarelo/roxo da marca).

## Onde já foi usado
- **Kairogen** (`mcp__Kairogen__*`): `generate_video` com `first_frame_url` = uma destas imagens
  (ou a imagem de referência original gerada em 15/11/2026, que deu origem a estas) + modelo
  **veo3-1-lite**, reaproveitando a mesma imagem em todas as cenas pra manter o personagem
  consistente. 2 Reels de Black Friday já agendados (`2026-11-20-reel-bf-pesquisa`,
  `2026-11-25-reel-bf-corre`) e 2 Stories em vídeo (`2026-11-16-story-mascote-gratidao`,
  `2026-11-17-story-mascote-black-friday`).

## Google Flow (Veo 3.1) — pesquisado em 15/11/2026, ainda não usado com o Binguinho
Confirmado por pesquisa (não só memória, regra do Herlison de 14/11): o Veo 3.1 tem o recurso
**"Ingredients to Video"**, disponível dentro do Flow — permite enviar até 3 imagens de referência
(rosto/personagem, traje, cenário) e o modelo mantém o personagem consistente nas cenas geradas, em
vez de recriar do zero a partir só de texto. É o recurso que faltava pra incluir o Binguinho nos
Reels do Flow (até aqui, `dados/flow/PROMPTS.md` só gerava cenas genéricas sem personagem, de
propósito, por não ter como travar a identidade).
- Como usar: no Flow, clicar no nome do modelo na caixa de prompt > escolher **Video > Ingredients**,
  subir `binguinho_referencia.jpg` (e opcionalmente `binguinho_comemorando.jpg` pra variar a pose) e
  escrever o prompt da cena normalmente, descrevendo a AÇÃO (não a aparência, que já vem da
  imagem).
- Ainda não confirmado: se o plano gratuito do Herlison no Flow já libera o modo Ingredients (o
  recurso é do Veo 3.1; o plano dele hoje gera com **Veo 3.1 Lite**) — testar na prática antes de
  prometer o resultado.
- Regra de uso continua a mesma do `PROMPTS.md`: sem texto/logo/preço na imagem gerada pela IA (eu
  sobreponho depois), 9:16, aprovar a geração uma vez no agente do projeto (nunca "Sempre aprovar").

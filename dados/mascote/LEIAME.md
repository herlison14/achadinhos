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

## Google Flow (Veo 3.1) — testado e funcionando em 15/11/2026
Confirmado na prática (depois de pesquisa de mercado, regra do Herlison de 14/11): o plano dele no
Flow **já libera personagem consistente**, mesmo gerando com **Veo 3.1 Lite** (não precisou de
upgrade). O caminho real na interface não é "Ingredients to Video" direto na caixa de prompt — é a
aba **Personagens** (menu lateral esquerdo do projeto):
1. Personagens > "Novo personagem" > subir `binguinho_referencia.jpg` (e opcionalmente
   `binguinho_comemorando.jpg`) > o Flow gera um retrato com o modelo "Nano Banana 2.1" > renomear
   para "Binguinho" > Concluir. Fica salvo na mídia do projeto, reaproveitável em qualquer cena nova.
2. Em qualquer prompt de vídeo, digitar `@Bingu` (ou `@Binguinho`) na caixa de comando > o buscador
   de recursos mostra o personagem "Binguinho" (ícone de personagem, não confundir com os vídeos
   gerados que aparecem na mesma lista) > clicar nele > escrever o resto do prompt descrevendo só a
   AÇÃO da cena (a aparência já vem do personagem).
3. O agente sempre pede confirmação antes de gerar (10 créditos por cena de 8s no Veo 3.1 Lite) —
   aprovar uma vez, nunca "Sempre aprovar" (regra já valia pro Kairogen, vale igual aqui).
Resultado: 3 cenas testadas (corredor de lasers, desarmando bomba, caixa revela presente de Black
Friday) saíram com o Binguinho visualmente idêntico ao personagem salvo em todas — identidade
mantida sem repetir a imagem de referência a cada prompt (o `@menção` já resolve isso).

**Áudio nativo do Veo 3.1 (confirmado por pesquisa de mercado em 15/11/2026):** o modelo gera
música, efeitos sonoros e até narração/fala JUNTO com o vídeo, descritos em texto no mesmo prompt
("música de suspense tocando no fundo", "uma voz narra: ...") — não é um prompt separado nem uma
ferramenta à parte. Ressalva importante: o suporte oficial a fala do Veo 3.1 lista só inglês,
chinês, japonês, coreano e espanhol — **português não está na lista oficial**. Testei mesmo assim
pedindo narração em PT-BR numa cena (CTA de Black Friday) e o rosto do personagem mostrou
movimento de boca condizente com fala (sinal visual de que tentou gerar a voz), mas eu não tenho
como ouvir o áudio pra confirmar se saiu inteligível — **isso precisa de confirmação do Herlison
ouvindo o resultado**. Se a narração em português sair ruim, o plano B é manter música/efeitos só
(que funcionam bem, línguas à parte) e levar o texto da chamada pra tela via overlay de ffmpeg, no
padrão dos outros Reels, em vez de voz.

**Texto na tela gerado pelo próprio Veo:** pedi uma etiqueta escrita "BLACK FRIDAY" no presente da
cena final e saiu legível e bem posicionada — melhor do que a experiência anterior com o Flow
"agente" de primeiro/último frame (05/11/2026, que cortava letras em close). Mesmo assim, por
segurança, textos de marca importantes (nome da loja, preço) continuam sendo sobrepostos depois
via ffmpeg, não gerados pela IA.

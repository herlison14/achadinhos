# Esquenta de Natal 2026 — plano (criado em 02/11/2026)

Natal: 25/12/2026. Black Friday: 27/11/2026. Tudo de Natal vai ao ar **depois do 11.11** (a partir de 17/11).

## Já pronto e agendado (sem preço, `dados/reels.json`, robô do Instagram, 20:00)
17/11 lista de presentes · 19/11 prazo de entrega · 21/11 presente pra criança · 29/11 faltam 26 dias · 01/12 lista da ceia ·
03/12 decoração · 06/12 amigo secreto · 10/12 ache seu presente no site · 15/12 faltam 10 dias · 20/12 faltam 5 dias.
A tarefa semanal "Reels da semana" completa até 5 por semana nos demais dias (sem repetir tema nem horário).

## Falta (precisa do Chrome dele ligado e dos links gerados por ele)
Meta: cerca de 30 produtos de Natal por loja (Amazon, Magalu, Mercado Livre, Shopee, AliExpress), no mesmo padrão do site
(`dados/itens.json`: preço só com conferência na loja e data; nada de preço, estoque ou desconto inventado).

Distribuição sugerida por loja (30): decoração e árvore/luzes 8 · mesa e cozinha 4 · brinquedos (selo do Inmetro) 6 ·
presentes (beleza, autocuidado, eletrônicos, moda) 8 · alimentos (panetone, chocolates, cestas; sem bebida alcoólica) 4.
Categorias existentes no site: Casa e cozinha, Beleza e cuidados, Mercado e guloseimas, Moda esporte e eletrônicos,
Infantil e brinquedos. Itens de Natal entram nelas (campo `cat`); uma página `ofertas/natal/` pode ser gerada por
palavra-chave no nome.

Quem faz o quê:
- Amazon e Magalu: eu monto o link (Amazon `https://www.amazon.com.br/dp/ASIN?tag=herlisonsanto-20`; Magalu dentro de
  magazinevoce.com.br/magazinein_400408/) e confiro preço pelo Chrome dele.
- Mercado Livre: ele gera os `meli.la` no gerador de links dele, em lote (1 URL por linha); eu passo a lista de anúncios.
- Shopee e AliExpress: links gerados por ele nos portais de afiliado; eu passo a lista de produtos.
- Depois: `vigia.py novo`/`atualizar`, `build`, `sincronia.py`, push. Posts de produto (carrossel/Reel "Caiu de preço") só
  com preço conferido há no máximo 7 dias.

## Fatos de pesquisa usados (sem número nos posts)
- Estudo da Shopee (matéria do E-Commerce Brasil, 09/12/2025): a maioria pretende comprar presentes; vestuário, casa,
  beleza e eletrônicos são as categorias mais citadas; brinquedos são os itens específicos mais desejados para crianças;
  quase metade começa a buscar com 3 semanas ou mais de antecedência.
- Dicas gerais (Portal de Prefeitura, 21/10/2025): conferir prazo de entrega, reputação do vendedor e política de troca;
  pesquisar cedo.
- Tendências de decoração 2026 (Correio Braziliense, Correio 24 Horas): árvores elegantes/maximalistas, tom perolado em alta.

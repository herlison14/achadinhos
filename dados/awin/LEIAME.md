# Awin — Achadinhos do Binga (afiliado 3147693, pessoa física)

Atualizado em 11/11/2026. Comissão e ganhos NUNCA entram neste arquivo (repositório público).

## Programas

| Loja | Programa (awinmid) | Situação | No site | Canais |
|---|---|---|---|---|
| KaBuM! | 17729 | aprovado 09/11/2026 | sim (4 itens) | site, Instagram, Telegram, WhatsApp |
| Nike | 17652 | aprovado 09/11/2026 | sim (3 itens) | site, Instagram, Telegram, WhatsApp |
| Dafiti | 17697 | aprovado 09/11/2026 | sim (4 itens, 11/11/2026) | site, Instagram, Telegram, WhatsApp |
| adidas | 79926 | aprovado 09/11/2026 | ainda não | só site e Instagram (termos: sem Telegram/WhatsApp/DM) |
| Doce Beleza | 76888 | aprovado 10/11/2026 (domínio docebeleza.com.br) | sim (4 itens, 11/11/2026) | site, Instagram, Telegram, WhatsApp |
| Avon | 23993 | recusado (não aceita pessoa física) | não | — |
| Eudora, Natura, O Boticário, JBL (10/11/2026) | — | recusados (não aceitam pessoa física) | — | — |
| Havaianas, Olympikus, Electrolux, Beleza na Web, L'Occitane au Brésil, Jequiti | — | pendentes (sem e-mail até 11/11/2026) | — | — |

Comissão da Nike e da adidas mudou em 10/11/2026 (valores só no painel da Awin). Doce Beleza: preço exibido na loja (sem desconto Pix informado); fotos em `www.docebeleza.com.br/cdn/shop/files/` (CSP liberado).

## Link de afiliado (deeplink)
`https://www.awin1.com/cread.php?awinmid=<programa>&awinaffid=3147693&ued=<URL do produto codificada>`
(`urllib.parse.quote(url, safe='')`). A sincronia recusa link sem `awinaffid=3147693` ou com destino em outra loja.

## O que o sistema já faz com as lojas da Awin
- Site, páginas `lojas/<loja>/`, filtro, banner, painel, cards do Instagram, Telegram/WhatsApp (adidas fora), robô de respostas (adidas fora).
- Contador de cliques (`cliques.js`) separa KaBuM!, Nike, Dafiti e adidas pelo destino do link.
- Ganhos: o painel e `tools/vendas.py` aceitam no CSV os nomes da Awin ("Kabum BR", "Nike BR", "KaBuM!"...).
  O Worker `cliques-binga` só aceita as lojas novas depois de colar o `worker/bloco_2_api_ganhos.js` atualizado.

## Perfil na Awin (texto pronto para colar em ui.awin.com > Conta > Perfil)
**Descrição curta:** Achadinhos do Binga: curadoria diária de ofertas com preço conferido na loja e data da conferência, no Instagram @achadinhosdobinga e no site achadinhosdobinga.com.br.

**Sobre / público:** Página brasileira de achadinhos e ofertas. Publico carrosséis, Reels e Stories todos os dias no Instagram e mantenho um site com mais de 240 ofertas de 7 lojas, separadas por categoria (casa e cozinha, beleza, moda e esporte, eletrônicos, infantil, pet e ferramentas). Todo preço é conferido na loja e mostra a data da conferência; não divulgo desconto que não existe. Público: consumidores brasileiros que compram pelo celular e querem economizar em compras do dia a dia e em datas como 11.11, Black Friday e Natal.

**Canais:** Instagram https://instagram.com/achadinhosdobinga · Site https://achadinhosdobinga.com.br · Telegram https://t.me/achadinhosdobinga · Canal do WhatsApp "Achadinhos do Binga".

**Exemplos de conteúdo:** carrossel "4 achados de tecnologia na KaBuM!" (preço no Pix conferido na loja) e o site com a seção "Caiu de preço", que compara cada preço com a conferência anterior.

**Tipo de promoção:** Conteúdo / Influenciador (redes sociais) e site de comparação/curadoria. Sem anúncio pago com a marca, sem e-mail marketing, sem cupom não autorizado.

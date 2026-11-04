# Vitrines por loja: como manter tudo junto

Regra do Herlison (03/11/2026): toda mudança de produto, de site ou de Instagram vale também para as lojas, ao mesmo tempo.

| Vitrine | Como atualiza |
|---|---|
| `lojas/<loja>/`, `ofertas/<categoria>/`, `ofertas/natal/` no site | Automático: `python3 -I tools/vigia.py build` regenera tudo a partir de `dados/itens.json`. |
| Lista ML "Minhas recomendações" (`listas.json` → `meli_geral`) | Via Chrome do Herlison (logado), na tarefa diária (Parte 3). Só entra item `meli` do `itens.json`. |
| Lista ML "Natal 2026 Achadinhos" (`listas.json` → `meli`) | Mesma ideia, só itens de `ids.json` (Natal). |
| Magalu, Amazon, Shopee, AliExpress | Sem vitrine/coleção para afiliado: vale só o site. |

## Adicionar um item do ML numa lista (testado em 03/11/2026)
1. Abrir o `href` (meli.la) do item no Chrome; ele redireciona para o perfil social. Ler `"item_id":"MLB..."` no HTML (`document.documentElement.innerHTML.match(/"item_id":"(MLB\d+)"/)`).
2. Em uma aba `myaccount.mercadolivre.com.br`, chamar `PUT /gz/navigation/api/wishlist/elements/override` com
   `{entity_id:"MLB<item_id>",entity_type:"item",entity_data:{attributes:[]},platform:"marketplace",platform_id:1,list_ids:["follow_id","<id-da-lista>"]}`.
   Ids das listas: Natal `153088ae-3263-4303-81d3-5a4137c46a1e`; recomendações `c3701385-e5ee-47de-9a3f-fd3c2b2350fc`.
3. Conferir a contagem na página da lista (`/bookmarks/wishlist/hub/detail/<id-da-lista>`).
- Item removido do `itens.json`: tirar da lista pela tela da lista (botão "Excluir"); se não der, avisar o Herlison.
- Limites do ML: no máximo 2 listas de afiliado; nome da lista até 25 caracteres. Tornar pública/privada e compartilhar é ação dele.

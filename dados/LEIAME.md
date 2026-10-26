# Dados do Achadinhos do Binga

- `itens.json`: as ofertas da página (nome, loja, categoria, link de afiliado, foto, preço, data da última conferência AAAA-MM-DD). **Fonte de verdade**: o `index.html` é gerado a partir daqui.
- `historico.json`: preço de cada oferta por dia (`id -> [[data, preço], ...]`). Não guarda IP nem dados de visitantes.
- `../tools/vigia.py`: ferramenta (Python 3, sem instalar nada).

## Rotina semanal
1. Conferir os preços nas lojas e montar um CSV `id_ou_link;preco;data` (ex.: `a1eb8e1a;18,90;27/10/2026`).
2. `python3 tools/vigia.py atualizar precos.csv` (grava histórico e mostra quedas/altas).
3. `python3 tools/vigia.py build` (regera o `index.html`; itens sem conferência há mais de 30 dias saem da página).
4. `python3 tools/vigia.py relatorio` (quedas recentes e itens sem conferência há mais de 7 dias).
5. Commit e push; a Cloudflare Pages publica.

Para incluir ou remover uma oferta, edite `itens.json` e rode o `build`. O texto de `nome`, `ex`, `pre`, `pos` e `cta` é HTML já escapado (use `&amp;` para `&`).

# Conferidor de preços no celular (S20 FE, Termux)

Lê o preço de cada oferta com o IP de casa (as lojas bloqueiam a nuvem) e alimenta o `vigia.py`.
Script: `tools/conferidor_celular.py`. Instalação: `tools/instalar_celular.sh`.

## Instalar (1 comando no Termux, F-Droid)
```
pkg update -y && pkg install -y git
git clone https://github.com/herlison14/achadinhos ~/achadinhos && bash ~/achadinhos/tools/instalar_celular.sh
```
O instalador abre o login do GitHub (código no navegador) e faz um teste que não grava nada. A rodada diária das 10h só é ligada depois da validação: `bash ~/achadinhos/tools/instalar_celular.sh --agendar`.

## Uso
- Teste: `python3 -I tools/conferidor_celular.py --limite 30`
- De verdade: `python3 -I tools/conferidor_celular.py --aplicar --limite 120` (grava, `vigia build`, `sincronia`, commit e push; se a sincronia falhar, desfaz).
- Log: `~/conferidor.log`. CSVs: `~/achadinhos-saida/`.

## Regras
- Só entra preço realmente lido; variação acima de 25% não é gravada (vai para "CONFERIR À MÃO").
- Fora do celular: Shopee e AliExpress (navegador logado) e adidas (termos proíbem leitura automática): continuam na rotina do computador.
- Amazon e lojas Awin são lidas pela página da loja (sem clicar no link de afiliado); `meli.la` é aberto uma vez e o destino fica em cache (`~/.achadinhos_cache_urls.json`).
- Legendas de posts agendados NÃO são corrigidas pelo celular: a sincronia avisa e a rotina do Claude ajusta.

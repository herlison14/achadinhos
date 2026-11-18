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
- Teste (calibra; não grava): `python3 -I tools/conferidor_celular.py --limite 150`
- De verdade: `python3 -I tools/conferidor_celular.py --aplicar --limite 120` (grava, `vigia build`, `sincronia`, commit e push; se a sincronia falhar, desfaz).
- Log: `~/conferidor.log`. CSVs: `~/achadinhos-saida/`.

## Proteções (todas verificadas no simulador)
- **Calibração:** o teste compara a leitura com o preço já registrado e só libera as lojas em que >= 70% batem (até 2%). Sem teste prévio o `--aplicar` não roda. Evita gravar preço de tabela quando o site usa o Pix. Loja nova na fila é liberada sozinha para a rodada seguinte se tiver >= 8 leituras e >= 80% fiéis; loja que deixa de bater (< 50%) é travada até novo teste.
- **Item em post/Story agendado:** se o preço mudou fica PRESO (a legenda e o card trazem o preço; mudar sem corrigir faz o publicador bloquear o post). Se não mudou, só renova a data. Quem corrige legenda e card é a rotina do Claude.
- **Corrida com outros robôs:** se o push for recusado, o celular refaz tudo sobre a versão nova do GitHub e descarta linha de item que outro robô acabou de atualizar.
- **Heartbeat:** `dados/celular.json` (só contagens: lidos, aplicados, presos, bloqueios, hora) mostra se o celular está vivo.
- Variação acima de 25% não é gravada (`--limite-variacao 0.4` para ampliar): na Black Friday, quedas grandes legítimas aparecem em "CONFERIR À MÃO".

## Simulador (ambiente de teste)
`python3 -I tools/simulador_celular.py` (ou `S2 S5`...): monta GitHub falso, celular, outro escritor e lojas falsas (captcha, 403/429, 500, lento, esgotado, preço de tabela x Pix, variantes) e roda 17 cenários / 53 verificações sobre o código real. Rodar de novo sempre que mexer no conferidor, no `vigia.py` ou no publicador. Ele NÃO prova que as lojas reais aceitam o celular nem que o HTML real bate com os extratores: isso só o teste no celular responde.

## Regras
- Só entra preço realmente lido; variação acima de 25% não é gravada (vai para "CONFERIR À MÃO").
- Fora do celular: Shopee e AliExpress (navegador logado) e adidas (termos proíbem leitura automática): continuam na rotina do computador.
- Amazon e lojas Awin são lidas pela página da loja (sem clicar no link de afiliado); `meli.la` é aberto uma vez e o destino fica em cache (`~/.achadinhos_cache_urls.json`).
- Legendas de posts agendados NÃO são corrigidas pelo celular: a sincronia avisa e a rotina do Claude ajusta.

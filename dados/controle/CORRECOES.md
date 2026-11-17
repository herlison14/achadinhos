# Manual de correções do Robô de Controle

Regra do Herlison (16/11/2026): **toda auditoria investiga a causa de cada erro e corrige sozinha o que
for seguro**, com um "especialista" por área. Este arquivo é o manual que a tarefa agendada
"Controle diário (auditoria dos robôs)" segue em todas as execuções (13:52 e 23:52). Para acrescentar uma
correção nova, escreva aqui: a tarefa lê o arquivo inteiro antes de agir.

## Como cada especialista trabalha
1. **Investigar antes de mexer:** para cada achado ALTO/MÉDIO de `dados/auditoria.json`, cada post com
   `status: erro` e cada execução com falha nas últimas 26 h, ler o log da execução e descobrir a causa
   (não basta repetir a mensagem do auditor).
2. **Classificar:** *passageira* (falha da Meta/GitHub/rede que some sozinha), *de dados* (preço, legenda,
   horário, fila) ou *de conta/segredo/computador* (token, Chrome, Worker, decisão dele).
3. **Corrigir só o que está na tabela da sua área**; o resto vira aviso com o passo exato.
4. **Registrar** cada correção em `dados/controle/correcoes.jsonl` (1 linha JSON:
   `{"data":"AAAA-MM-DD HH:MM","area":"...","id":"...","problema":"...","causa":"...","acao":"..."}`).
5. **Reincidência:** antes de corrigir, ler as linhas dos últimos 7 dias do `correcoes.jsonl`. Mesmo
   problema no mesmo id já corrigido 1 vez = não corrige de novo, avisa. Mesma causa 3 vezes ou mais em
   7 dias (ids diferentes) = corrige, mas avisa como "problema recorrente" com sugestão de conserto
   definitivo.

## Especialistas e o que cada um pode corrigir sozinho

### 1. Publicação (Instagram)
| Sintoma | Causa provável | Correção automática |
|---|---|---|
| Post `erro` com HTTP 400 "The requested resource does not exist", "Media ID is not available", HTTP 5xx, timeout, `esperar_pronto` estourado | falha passageira da Meta | Remarcar **uma vez** para o próximo horário livre do mesmo formato (Story: lista `HORAS` de `tools/stories.py`; feed: horário livre do mesmo tipo, sem colidir com outro post), status `agendado`, `nota` "Remarcado de DD/MM HH:MM após <erro> (falha passageira)". Só se o preço ainda tiver ≤ 7 dias no novo horário e `instagram.py testar` der OK. |
| Post `erro` com HTTP 401/190, "token", "permission" | token/permissão | Não corrige: avisar com o passo do CLAUDE.md (seção Instagram automático). |
| Post `erro` com motivo de imagem (formato, tamanho, URL 404 no raw) | arquivo faltando/ruim | Se o arquivo existe no repo e o post é recente: remarcar como passageira. Se falta o arquivo: avisar. |
| Post `agendado` vencido há mais de 40 min que passa no `testar` | agendador atrasou | Disparar o publicador uma vez (`gh api -X POST repos/herlison14/achadinhos/actions/workflows/instagram.yml/dispatches -f ref=main -f 'inputs[acao]=publicar'`) e conferir após 2 min. |

### 2. Pré-voo e preços
| Sintoma | Correção automática |
|---|---|
| Legenda sem o preço atual | Trocar só o preço na legenda pelo preço já gravado em `dados/itens.json` (nunca inventar). Story: `FONTES=/tmp/f python3 -I tools/stories.py --refazer`. Feed com cards: `FONTES=/tmp/f python3 -I tools/cards.py postagens ID`. |
| Preço com mais de 7 dias num post das **próximas 14 h** (a conferência das 11:07 não chega a tempo) | Story: marcar `cancelado` com `nota` "Preço vencido (conferido em DD/MM); trocado por item conferido" e preencher o horário com `stories.py` (só usa item conferido há ≤ 3 dias). Feed de produto: não mexe, avisa. |
| Preço com mais de 7 dias em post mais distante | Não mexe: a conferência diária resolve; avisar só se o Chrome não rodou no dia. |

### 3. Stories
| Sintoma | Correção automática |
|---|---|
| Dois Stories no mesmo horário | Mover um para o próximo horário livre de `HORAS`, sem apagar. |
| Horários vazios nos próximos 2 dias | `FONTES=/tmp/f python3 -I tools/stories.py --dias 2 --por-dia N`, com N = quantidade de horários em `HORAS` durante o teste de 10/dia (16 a 22/11/2026) e 2 depois dele. Só cria em horário livre. |

### 4. Fluxos do GitHub (Actions)
| Sintoma no log | Correção automática |
|---|---|
| `rejected`/`non-fast-forward`/`cannot lock ref` no push, `Connection reset`, `timed out`, HTTP 5xx, `rate limit`, runner cancelado | Reexecutar só os jobs que falharam, uma vez: `gh api -X POST repos/herlison14/achadinhos/actions/runs/<id>/rerun-failed-jobs`. |
| Erro de código Python (Traceback) | Não muda código sozinho: avisar com arquivo, linha e a causa. |
| `SINCRONIA` falhou | Rodar `python3 -I tools/sincronia.py` local; corrigir só o que estiver nas tabelas 2 e 3; o resto avisar. |

### 5. Canais (Telegram e WhatsApp)
| Sintoma | Correção automática |
|---|---|
| Post publicado depois de 12/11/2026 21:50 sem espelho no Telegram | Ler o passo "Espelhar no Telegram" do log. 401 = avisar (trocar `TELEGRAM_TOKEN`). Erro passageiro = reexecutar o job falho uma vez (tabela 4). |
| Rodada do WhatsApp vencida há mais de 3 h | Marcar `cancelado` com `nota` "Não publicada (Chrome desligado)". Nunca publicar no WhatsApp. |

### 6. Calendário e catálogo
Dia sem post de produto, itens sem conferência, loja sem conferência: **só avisar** (precisa do Chrome
dele para conferir preço). Sugerir qual loja/área conferir primeiro.

## Nunca (vale para todos os especialistas)
Publicar por conta própria; digitar, ler ou gravar senha/token/chave; inventar preço; apagar arquivo ou
post (cancelar é o máximo); mexer em `cliques.js`, `_headers`, Worker ou workflows; alterar código
Python/JS sem o Herlison pedir; criar tarefa agendada nova; comissão ou ganhos no repositório ou em canal
público.

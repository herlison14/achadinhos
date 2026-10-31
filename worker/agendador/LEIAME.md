# Worker `agendador-binga`

Dispara o robô do Instagram (`instagram.yml`, `acao=publicar`) no horário dos posts. O agendamento do próprio GitHub chegou a atrasar mais de 4 h; o cron da Cloudflare roda no minuto certo. Se o `posts.json` não tem post `agendado` vencido, não faz nada (não gasta execuções).

Montagem (uma vez, à mão, como o outro Worker):
1. GitHub > Settings > Developer settings > Fine-grained tokens: token só do repositório `herlison14/achadinhos`, permissão **Actions: Read and write**, validade 1 ano. O token só vai para a Cloudflare, nunca para o chat nem para o repositório.
2. Cloudflare > Workers & Pages > Create > Worker `agendador-binga` > Edit code: colar `worker.js` > Deploy.
3. Settings > Variables and Secrets > adicionar o segredo `GH_TOKEN` (tipo Secret).
4. Settings > Triggers > Cron Triggers: `*/10 * * * *`.
5. Teste: Logs (tempo real) mostram "nada no horário" ou "disparado para: ...".

Trocar o token antes de vencer. O cron do GitHub continua como reserva.

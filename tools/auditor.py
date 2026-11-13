#!/usr/bin/env python3
"""Robô de controle (auditor): confere se cada robô fez o que estava programado e se o que vem pela frente vai passar.

Roda no GitHub Actions (auditoria.yml) duas vezes por dia, depois das rodadas de publicação. Só lê os dados do
repositório e o histórico das execuções do GitHub; não publica nada e não usa nenhum segredo além do GITHUB_TOKEN
da própria execução (só para ler execuções e abrir/fechar o alerta).

Áreas conferidas (cada achado tem nível: ALTO = algo deixou de sair ou vai falhar; MEDIO = atenção; INFO):
  publicação   posts do Instagram vencidos e não publicados, posts com erro, Stories em dobro ou faltando
  pré-voo      posts das próximas 72 h passam pela mesma trava do publicador (preço, legenda, imagens, vídeo)?
  telegram     carrosséis publicados que não chegaram ao canal do Telegram
  whatsapp     rodadas do canal do WhatsApp que passaram do horário sem publicar
  robôs        execuções com falha nas últimas 26 h (todos os fluxos do repositório)
  preços       itens perto de sair do site (sem conferência) e posts futuros que o robô vai bloquear
  métricas     retrato do Instagram atualizado?
  calendário   dias das próximas 72 h sem post de produto, de crescimento ou Reel

Saída: dados/auditoria.json (público: só contagens e ids, sem segredo nem comissão), resumo da execução e,
se houver ALTO, uma issue "Auditoria: problemas" no GitHub (avisa o Herlison por e-mail/app); fecha sozinha quando zera.
Uso: python3 -I tools/auditor.py [--sem-github]
"""
import importlib.util, json, os, sys, urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone, date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BRT = timezone(timedelta(hours=-3))
REPO = os.environ.get("GITHUB_REPOSITORY", "herlison14/achadinhos")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HORAS_STORY = ("11:30", "18:30")


def ler(nome, padrao):
    try:
        return json.loads((RAIZ / "dados" / nome).read_text(encoding="utf-8"))
    except Exception:
        return padrao


def hora_post(p):
    return datetime.fromisoformat("%sT%s:00" % (p["data"], p.get("hora") or "12:00")).replace(tzinfo=BRT)


def gh(metodo, caminho, dados=None):
    req = urllib.request.Request("https://api.github.com/repos/%s%s" % (REPO, caminho), method=metodo,
                                 data=json.dumps(dados).encode() if dados is not None else None,
                                 headers={"Authorization": "Bearer " + TOKEN, "Accept": "application/vnd.github+json",
                                          "User-Agent": "achadinhos-auditor"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")


def publicador():
    esp = importlib.util.spec_from_file_location("instagram", RAIZ / "tools" / "instagram.py")
    m = importlib.util.module_from_spec(esp)
    esp.loader.exec_module(m)
    return m


def auditar(agora, usar_github):
    achados = []

    def add(nivel, area, texto, acao=""):
        achados.append({"nivel": nivel, "area": area, "texto": texto, "acao": acao})

    posts = ler("posts.json", [])
    itens_l = ler("itens.json", [])
    itens = {i["id"]: i for i in itens_l}
    hoje = agora.date()

    # ---- publicação no Instagram
    for p in posts:
        if p.get("canal", "ig") != "ig":
            continue
        atraso = (agora - hora_post(p)).total_seconds() / 60
        if p["status"] == "agendado" and atraso > 40:
            add("ALTO", "publicação", "%s (%s %s %s) passou %d min do horário e não saiu" % (
                p["id"], p.get("formato"), p["data"], p.get("hora"), atraso),
                "ver o log do Instagram (publicador); se o motivo for trava de preço, reconferir o item")
        if p["status"] == "erro":
            add("ALTO", "publicação", "%s está com erro: %s" % (p["id"], (p.get("nota") or "")[:160]),
                "corrigir o motivo e voltar o status para agendado")
        if p["status"] == "planejado" and 0 <= (hora_post(p) - agora).total_seconds() <= 48 * 3600:
            add("MEDIO", "publicação", "%s está só 'planejado' para %s %s (não vai sair sozinho)" % (
                p["id"], p["data"], p.get("hora")), "aprovar (agendado) ou cancelar")

    # Stories: um por horário, 2 por dia nos próximos 2 dias
    st = [p for p in posts if p.get("formato") == "story" and p["status"] in ("agendado", "publicado")]
    for (d, h), n in Counter((p["data"], p.get("hora")) for p in st).items():
        if n > 1 and datetime.fromisoformat("%sT%s:00" % (d, h)).replace(tzinfo=BRT) > agora:
            add("MEDIO", "publicação", "%d Stories no mesmo horário (%s %s)" % (n, d, h), "mover um para outro horário")
    for k in (1, 2):
        d = (hoje + timedelta(days=k)).isoformat()
        tem = {p.get("hora") for p in st if p["data"] == d}
        falta = [h for h in HORAS_STORY if h not in tem]
        if falta:
            add("MEDIO", "publicação", "sem Story em %s às %s" % (d, ", ".join(falta)),
                "rodar tools/stories.py (precisa de itens conferidos há até 3 dias)")

    # ---- pré-voo: os próximos 72 h passam pela trava do publicador?
    try:
        ig = publicador()
        for p in posts:
            if p.get("canal", "ig") != "ig" or p["status"] != "agendado":
                continue
            quando = hora_post(p)
            if not (agora - timedelta(minutes=40) <= quando <= agora + timedelta(hours=72)):
                continue
            erros = ig.validar(p, itens, quando, False)
            if erros:
                add("ALTO", "pré-voo", "%s (%s %s) vai ser BLOQUEADO: %s" % (p["id"], p["data"], p.get("hora"), "; ".join(erros)[:220]),
                    "reconferir o preço / ajustar a legenda antes do horário")
    except Exception as e:
        add("MEDIO", "pré-voo", "não consegui rodar a trava do publicador: %s" % type(e).__name__)

    # ---- Telegram (espelho dos carrosséis)
    for p in posts:
        pub = p.get("publicado_em") or ""
        if (p.get("canal", "ig") == "ig" and p["status"] == "publicado" and p.get("formato") != "story" and p.get("imagens")
                and not p.get("telegram_em") and pub >= "2026-10-31"):
            try:
                quando = datetime.fromisoformat(pub.replace(" ", "T") + ":00").replace(tzinfo=BRT)
            except ValueError:
                continue
            if (agora - quando).total_seconds() > 3600:
                add("ALTO", "telegram", "%s publicado no Instagram em %s não chegou ao canal do Telegram" % (p["id"], pub),
                    "ver o passo 'Espelhar no Telegram' do publicador (HTTP 401 = TELEGRAM_TOKEN do GitHub inválido)")

    # ---- WhatsApp (rodadas manuais pelo Chrome)
    for p in posts:
        if p.get("canal") == "wa" and p["status"] == "agendado" and (agora - hora_post(p)).total_seconds() > 3 * 3600:
            add("MEDIO", "whatsapp", "rodada %s (%s %s) não foi publicada" % (p["id"], p["data"], p.get("hora")),
                "publicar pelo WhatsApp Web (Chrome ligado) ou marcar como cancelado")

    # ---- preços e catálogo
    idade = lambda i: (hoje - date.fromisoformat(i["conferido"])).days
    velhos7 = [i for i in itens_l if idade(i) > 7]
    saindo = [i for i in itens_l if 25 <= idade(i) <= 30]
    fora = [i for i in itens_l if idade(i) > 30]
    if velhos7:
        add("MEDIO" if len(velhos7) < len(itens_l) / 2 else "ALTO", "preços",
            "%d de %d itens sem conferência há mais de 7 dias (não vão a Instagram/Telegram)" % (len(velhos7), len(itens_l)),
            "conferência diária pelo Chrome (tarefa das 11:07 precisa do computador ligado)")
    if saindo:
        add("MEDIO", "preços", "%d itens saem do site nos próximos dias (25 a 30 dias sem conferência)" % len(saindo), "reconferir")
    if fora:
        add("INFO", "preços", "%d itens já fora do site (mais de 30 dias)" % len(fora))
    lojas = Counter(i["loja"] for i in itens_l if idade(i) <= 7)
    tem = {i["loja"] for i in itens_l}
    for lj in ("shopee", "amazon", "meli", "magalu", "aliexpress", "kabum", "nike", "dafiti", "adidas", "docebeleza", "puma", "hope", "mizuno", "polishop"):
        if lj in tem and not lojas.get(lj):
            add("MEDIO", "preços", "nenhum item da loja %s conferido nos últimos 7 dias" % lj, "incluir na próxima conferência")

    # ---- métricas
    m = ler("metricas.json", {})
    try:
        ult = datetime.fromisoformat(m["atualizado"].replace(" ", "T")).replace(tzinfo=BRT)
        if (agora - ult).total_seconds() > 30 * 3600:
            add("MEDIO", "métricas", "métricas do Instagram sem atualizar desde %s" % m["atualizado"], "ver o fluxo metricas.yml")
    except Exception:
        add("MEDIO", "métricas", "dados/metricas.json ausente ou sem data")

    # ---- calendário dos próximos 3 dias
    for k in (0, 1, 2):
        d = (hoje + timedelta(days=k)).isoformat()
        dia = [p for p in posts if p["data"] == d and p.get("canal", "ig") == "ig" and p["status"] in ("agendado", "publicado")]
        prod = [p for p in dia if p.get("formato") in ("carrossel", "post") and not p.get("sem_preco")]
        cresc = [p for p in dia if p.get("formato") in ("carrossel", "post") and p.get("sem_preco")]
        reel = [p for p in dia if p.get("formato") == "reel"]
        falta = [n for n, l in (("produto", prod), ("crescimento", cresc), ("Reel", reel)) if not l]
        if falta:
            add("INFO" if k == 0 else "MEDIO", "calendário", "%s sem post de %s" % (d, ", ".join(falta)),
                "completar a programação")

    # ---- execuções dos robôs no GitHub (últimas 26 h)
    if usar_github and TOKEN:
        try:
            desde = (agora - timedelta(hours=26)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            runs = gh("GET", "/actions/runs?per_page=100&created=%3E" + desde)["workflow_runs"]
            falhas = Counter(r["name"] for r in runs if r.get("conclusion") == "failure")
            for nome, n in falhas.items():
                add("ALTO", "robôs", "fluxo '%s' falhou %d vez(es) nas últimas 26 h" % (nome, n), "abrir o log da execução")
            pub = [r for r in runs if r["name"].startswith("Instagram (publicador)")]
            if not pub:
                add("ALTO", "robôs", "nenhuma execução do publicador nas últimas 26 h", "conferir o agendador-binga (Cloudflare)")
        except Exception as e:
            add("MEDIO", "robôs", "não consegui ler as execuções do GitHub: %s" % type(e).__name__)

    return achados


def resumo_md(achados, agora):
    n = Counter(a["nivel"] for a in achados)
    linhas = ["## Auditoria %s" % agora.strftime("%d/%m/%Y %H:%M"),
              "", "ALTO: %d · MÉDIO: %d · INFO: %d" % (n["ALTO"], n["MEDIO"], n["INFO"]), ""]
    for nivel in ("ALTO", "MEDIO", "INFO"):
        for a in achados:
            if a["nivel"] == nivel:
                linhas.append("- **%s** [%s] %s%s" % (nivel, a["area"], a["texto"], (" → " + a["acao"]) if a["acao"] else ""))
    if not achados:
        linhas.append("Tudo conforme o programado.")
    return "\n".join(linhas) + "\n"


def alerta(achados, md):
    """Abre/atualiza a issue de alerta quando há ALTO; fecha quando não há."""
    abertas = gh("GET", "/issues?state=open&labels=auditoria&per_page=5")
    altos = [a for a in achados if a["nivel"] == "ALTO"]
    if altos:
        corpo = md + "\n_Gerado pelo robô de controle (tools/auditor.py). Fecha sozinha quando não houver mais nível ALTO._"
        if abertas:
            gh("PATCH", "/issues/%d" % abertas[0]["number"], {"body": corpo, "title": "Auditoria: %d problema(s) ALTO" % len(altos)})
        else:
            gh("POST", "/issues", {"title": "Auditoria: %d problema(s) ALTO" % len(altos), "body": corpo, "labels": ["auditoria"]})
    else:
        for i in abertas:
            gh("POST", "/issues/%d/comments" % i["number"], {"body": "Resolvido: a auditoria de agora não achou nível ALTO."})
            gh("PATCH", "/issues/%d" % i["number"], {"state": "closed"})


def main():
    usar_github = "--sem-github" not in sys.argv
    agora = datetime.now(BRT)
    achados = auditar(agora, usar_github)
    md = resumo_md(achados, agora)
    print(md)
    saida = {"gerado": agora.strftime("%Y-%m-%d %H:%M"),
             "contagem": dict(Counter(a["nivel"] for a in achados)), "achados": achados}
    (RAIZ / "dados" / "auditoria.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(md)
    if usar_github and TOKEN:
        try:
            alerta(achados, md)
        except Exception as e:
            print("(alerta no GitHub falhou: %s)" % type(e).__name__)
    return 0


if __name__ == "__main__":
    sys.exit(main())

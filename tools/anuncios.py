#!/usr/bin/env python3
"""Leitor de desempenho de anúncios pagos no Meta Ads (Facebook + Instagram), direto da API oficial da Meta —
sem depender de ferramenta paga de terceiro (Adspirer e afins, que tem limite de 15 chamadas/mês no plano Free).

Só LEITURA: nunca cria, pausa, retoma, muda orçamento ou gasta um centavo. Qualquer ação de escrita (pausar
campanha, mudar orçamento) é decisão do Herlison, feita por ele no Gerenciador de Anúncios ou pedida
explicitamente a mim, com valor e campanha nomeados — nunca de forma automática ou genérica ("otimiza os
anúncios" não autoriza nada aqui).

Reaproveita o segredo IG_TOKEN (token EAA do app "Achadinhos Publicador", gerado no Explorador da Graph API).
Esse token precisa da permissão `ads_read` — ela já apareceu na lista de permissões usadas para refazer o
IG_TOKEN no passado (ver CLAUDE.md, seção "Instagram automático"), mas pode não estar no token atual. O
comando `status` abaixo confere e avisa exatamente o que regenerar se faltar.

Variável de ambiente: IG_TOKEN (mesma do publicador do Instagram). Opcional: ADS_ACCOUNT_ID (id numérico, sem
o prefixo "act_"); sem ela, descobre sozinho a(s) conta(s) de anúncio ligada(s) ao token.

Comandos:
  python3 tools/anuncios.py status      confere o token e lista as contas de anúncio que ele alcança
  python3 tools/anuncios.py coletar     lê o desempenho dos últimos 30 dias e grava dados/anuncios.json
"""
import json, os, sys, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados" / "anuncios.json"
GRAPH = "https://graph.facebook.com/v21.0"
BRT = timezone(timedelta(hours=-3))


class ErroAPI(Exception):
    pass


def api(caminho, parametros=None):
    """Chama a API. O token vai no parâmetro e nunca é impresso."""
    tok = os.environ.get("IG_TOKEN", "")
    p = dict(parametros or {})
    p["access_token"] = tok
    corpo = urllib.parse.urlencode(p)
    try:
        r = urllib.request.urlopen(f"{GRAPH}{caminho}?{corpo}", timeout=60)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            erro = json.loads(e.read()).get("error", {})
        except Exception:
            erro = {}
        raise ErroAPI("%s %s (code=%s, subcode=%s)" % (
            e.code, erro.get("message", ""), erro.get("code"), erro.get("error_subcode")))


def ler(p, padrao):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return padrao


def gravar(p, obj):
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")


def contas_de_anuncio():
    """Lista as contas de anúncio que o token alcança (id, nome, moeda, status)."""
    return api("/me/adaccounts", {"fields": "account_id,name,currency,account_status"}).get("data", [])


def escolher_conta():
    conta_id = os.environ.get("ADS_ACCOUNT_ID", "").strip()
    if conta_id:
        return conta_id
    contas = contas_de_anuncio()
    if not contas:
        raise ErroAPI("o token não alcança nenhuma conta de anúncio (sem permissão ads_read, "
                       "ou a conta não está ligada a este usuário/app).")
    return contas[0]["account_id"]


def cmd_status():
    if not os.environ.get("IG_TOKEN"):
        print("::error::IG_TOKEN não configurado (Settings > Secrets > Actions).")
        return 3
    try:
        contas = contas_de_anuncio()
    except ErroAPI as e:
        print("::error::o token atual não consegue listar contas de anúncio (%s). Gere de novo no Explorador da "
              "Graph API (developers.facebook.com/tools/explorer), app Achadinhos Publicador, marcando a "
              "permissão `ads_read` (além das que já usa), e troque o segredo IG_TOKEN." % e)
        return 1
    if not contas:
        print("::error::token válido, mas sem nenhuma conta de anúncio vinculada a ele.")
        return 1
    for c in contas:
        print("%s  %-30s  moeda %s  status %s" % (
            c["account_id"], c.get("name", ""), c.get("currency", ""), c.get("account_status")))
    return 0


def cmd_coletar():
    try:
        conta = escolher_conta()
    except ErroAPI as e:
        print("::error::%s" % e)
        return 1
    camp = api("/act_%s/campaigns" % conta,
                {"fields": "id,name,status,objective,effective_status", "limit": 100}).get("data", [])
    por_id = {c["id"]: c for c in camp}
    ins = api("/act_%s/insights" % conta, {
        "level": "campaign",
        "date_preset": "last_30d",
        "fields": "campaign_id,spend,impressions,clicks,reach,ctr,cpc,outbound_clicks,actions",
        "limit": 200,
    }).get("data", [])
    linhas = []
    total_gasto = 0.0
    for i in ins:
        c = por_id.get(i.get("campaign_id"), {})
        gasto = float(i.get("spend", 0) or 0)
        total_gasto += gasto
        cliques_saida = next((int(float(x.get("value", 0))) for x in (i.get("outbound_clicks") or [])
                               if x.get("action_type") == "outbound_click"), None)
        linhas.append({
            "campanha": c.get("name", i.get("campaign_id")),
            "status": c.get("effective_status", c.get("status", "")),
            "objetivo": c.get("objective", ""),
            "gasto": round(gasto, 2),
            "impressoes": int(i.get("impressions", 0) or 0),
            "cliques": int(i.get("clicks", 0) or 0),
            "cliques_saida": cliques_saida,
            "alcance": int(i.get("reach", 0) or 0),
            "ctr": round(float(i.get("ctr", 0) or 0), 2),
            "cpc": round(float(i.get("cpc", 0) or 0), 2),
        })
    dados = {
        "atualizado": datetime.now(BRT).strftime("%Y-%m-%d %H:%M"),
        "conta": conta,
        "periodo": "últimos 30 dias",
        "total_gasto": round(total_gasto, 2),
        "campanhas": linhas,
    }
    gravar(SAIDA, dados)
    print("%d campanha(s) com dado no período, gasto total R$ %.2f (30 dias)." % (len(linhas), total_gasto))
    return 0


if __name__ == "__main__":
    if os.environ.get("IG_TOKEN"):
        # tira espaços/quebras/aspas que costumam vir junto ao colar o segredo no GitHub
        os.environ["IG_TOKEN"] = "".join(os.environ["IG_TOKEN"].split()).strip("\"'")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    sys.exit({"status": cmd_status, "coletar": cmd_coletar}.get(cmd, lambda: sys.exit(__doc__))())

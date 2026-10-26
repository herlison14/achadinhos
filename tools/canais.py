#!/usr/bin/env python3
"""Gera (e, no Telegram, envia) as publicações dos canais a partir de dados/itens.json.

Uso:
  python3 -I tools/canais.py boasvindas [--origem wa|tg]
  python3 -I tools/canais.py ofertas [-n 4] [--origem wa|tg] [--registrar]
  python3 -I tools/canais.py enviar-telegram ofertas [-n 4]      # usa TELEGRAM_TOKEN e TELEGRAM_CHAT (variáveis de ambiente)

Regras: só entram itens conferidos nos últimos 7 dias; nunca repete item já enviado
(dados/canais.json); no máximo 1 item por loja por rodada, para variar; nada de preço
inventado: o texto sempre diz a data da conferência. O token do bot NUNCA fica no repositório.
"""
import json, os, sys, urllib.request, urllib.parse
from datetime import date, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ITENS = RAIZ / "dados" / "itens.json"
LOG = RAIZ / "dados" / "canais.json"
SITE = "https://achadinhosdobinga.com.br"
LOJAS = {"shopee": "Shopee", "amazon": "Amazon", "meli": "Mercado Livre",
         "aliexpress": "AliExpress", "magalu": "Magalu"}
AVISO = "Publicidade: links de afiliado. Preços e estoque mudam: confira na loja."


def ler(p, padrao):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return padrao


def br(iso):
    a, m, d = iso.split("-")
    return f"{d}/{m}/{a}"


def escolher(n, hoje=None):
    hoje = hoje or date.today()
    ja = set(ler(LOG, {"enviados": []}).get("enviados", []))
    ok = []
    for i in ler(ITENS, []):
        try:
            idade = (hoje - datetime.strptime(i["conferido"], "%Y-%m-%d").date()).days
        except Exception:
            continue
        if idade <= 7 and i["id"] not in ja and i.get("preco") and i.get("href"):
            ok.append(i)
    ok.sort(key=lambda i: (i["conferido"], i["id"]), reverse=True)
    por_loja, saida = {}, []
    for i in ok:                       # 1 por loja primeiro
        if i["loja"] not in por_loja:
            por_loja[i["loja"]] = 1
            saida.append(i)
    for i in ok:                       # completa se faltar
        if len(saida) >= n:
            break
        if i not in saida:
            saida.append(i)
    return saida[:n]


def texto_ofertas(itens, origem):
    if not itens:
        return None
    linhas = ["*Achadinhos do Binga* — ofertas conferidas", ""]
    for i in itens:
        nome = i["nome"].replace("&#x27;", "'")
        linhas.append(f"• {nome}\n  R$ {i['preco']} na {LOJAS.get(i['loja'], i['loja'])} "
                      f"(conferido em {br(i['conferido'])})\n  {i['href']}")
    linhas += ["", f"Mais ofertas: {SITE}/?o={origem}", "", AVISO]
    return "\n".join(linhas)


def texto_boasvindas(origem):
    return (f"*Achadinhos do Binga*\n\n"
            "Aqui eu separo achadinhos e ofertas de Shopee, Amazon, Mercado Livre, AliExpress e Magalu, "
            "sempre com a data em que o preço foi conferido. Sem preço inventado: se mudar, o preço da loja vale.\n\n"
            f"Todas as ofertas organizadas por categoria: {SITE}/?o={origem}\n\n{AVISO}")


def registrar(itens):
    d = ler(LOG, {"enviados": []})
    for i in itens:
        if i["id"] not in d["enviados"]:
            d["enviados"].append(i["id"])
    LOG.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def telegram(texto):
    tok, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT")
    if not tok or not chat:
        sys.exit("Defina TELEGRAM_TOKEN e TELEGRAM_CHAT no ambiente (nunca no repositório).")
    dados = urllib.parse.urlencode({"chat_id": chat, "text": texto, "parse_mode": "Markdown",
                                    "disable_web_page_preview": "true"}).encode()
    r = urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", dados, timeout=30)
    print("Telegram:", json.loads(r.read()).get("ok"))


def arg(a, nome, padrao):
    return a[a.index(nome) + 1] if nome in a else padrao


def main(a):
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == "boasvindas":
        print(texto_boasvindas(arg(a, "--origem", "wa")))
    elif cmd == "ofertas":
        itens = escolher(int(arg(a, "-n", 4)))
        t = texto_ofertas(itens, arg(a, "--origem", "wa"))
        if not t:
            sys.exit("Sem itens novos conferidos nos últimos 7 dias.")
        print(t)
        if "--registrar" in a:
            registrar(itens)
    elif cmd == "enviar-telegram":
        itens = escolher(int(arg(a, "-n", 4)))
        t = texto_boasvindas("tg") if a[1:2] == ["boasvindas"] else texto_ofertas(itens, "tg")
        if not t:
            sys.exit("Sem itens novos conferidos nos últimos 7 dias.")
        telegram(t)
        if a[1:2] != ["boasvindas"]:
            registrar(itens)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])

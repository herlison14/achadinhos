#!/usr/bin/env python3 -I
"""Relatório semanal "o que vendeu -> repetir".

Lê um CSV de ganhos no mesmo formato do painel (separador ';'):
    data;loja;produto;pedidos;comissao      (data DD/MM/AAAA, comissão 12,34)
e cruza o nome do produto com dados/itens.json e dados/posts.json para sugerir o
que repetir. Uso:

    python3 -I tools/vendas.py ganhos.csv [--dias 7] [--hoje AAAA-MM-DD] [--saida ~/relatorio.md]

REGRA DE SEGURANÇA: comissão/ganho NUNCA entra no repositório (público) nem no
Telegram. Por isso o relatório sai no terminal e, com --saida, só em arquivo FORA
do repositório (o script recusa gravar dentro dele).
"""
import argparse
import difflib
import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime, timedelta

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOJAS = {"shopee": "Shopee", "amazon": "Amazon", "meli": "Mercado Livre",
         "aliexpress": "AliExpress", "magalu": "Magalu"}


def sem_acento(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()


def loja_id(v):
    v = sem_acento(v)
    if v == "ml" or v.startswith("mercado"):
        return "meli"
    return v if v in LOJAS else ""


def num_br(v):
    v = str(v or "").strip().replace("R$", "").replace(" ", "")
    if "," in v:
        v = v.replace(".", "").replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return None


def brl(x):
    return "R$ " + f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def ler_csv(caminho):
    linhas, erros = [], []
    with open(caminho, encoding="utf-8-sig") as f:
        for n, l in enumerate(f, 1):
            l = l.strip()
            if not l:
                continue
            c = [x.strip() for x in l.split(";")]
            if n == 1 and "data" in c[0].lower():
                continue
            m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", c[0]) if c else None
            if len(c) < 5 or not m:
                erros.append(f"linha {n}: formato inesperado (data;loja;produto;pedidos;comissao)")
                continue
            loja, ped, com = loja_id(c[1]), c[3], num_br(c[4])
            if not loja or not c[2] or not ped.isdigit() or com is None:
                erros.append(f"linha {n}: loja/produto/pedidos/comissão inválidos")
                continue
            linhas.append({"dia": date(int(m[3]), int(m[2]), int(m[1])), "loja": loja,
                           "produto": c[2], "pedidos": int(ped), "comissao": com})
    return linhas, erros


def casar(produto, loja, itens):
    """Acha o item do catálogo mais parecido (mesma loja). Retorna (item, nota)."""
    alvo = re.sub(r"[^a-z0-9 ]", " ", sem_acento(produto))
    melhor, nota = None, 0.0
    for it in itens:
        if it["loja"] != loja:
            continue
        nome = re.sub(r"[^a-z0-9 ]", " ", sem_acento(it["nome"].replace("&amp;", "&")))
        r = difflib.SequenceMatcher(None, alvo, nome).ratio()
        if nome and (nome in alvo or alvo in nome):
            r = max(r, 0.9)
        if r > nota:
            melhor, nota = it, r
    return (melhor, nota) if nota >= 0.55 else (None, nota)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--dias", type=int, default=7)
    ap.add_argument("--hoje", help="AAAA-MM-DD (padrão: hoje)")
    ap.add_argument("--saida", help="arquivo .md FORA do repositório")
    a = ap.parse_args()

    if a.saida:
        dest = os.path.realpath(os.path.expanduser(a.saida))
        if dest == RAIZ or dest.startswith(RAIZ + os.sep):
            print("ERRO: comissão não pode ser gravada dentro do repositório público.", file=sys.stderr)
            return 2

    hoje = datetime.strptime(a.hoje, "%Y-%m-%d").date() if a.hoje else date.today()
    ini = hoje - timedelta(days=a.dias - 1)
    ini_ant, fim_ant = ini - timedelta(days=a.dias), ini - timedelta(days=1)

    linhas, erros = ler_csv(a.csv)
    itens = json.load(open(os.path.join(RAIZ, "dados", "itens.json"), encoding="utf-8"))
    posts = json.load(open(os.path.join(RAIZ, "dados", "posts.json"), encoding="utf-8"))
    postados = {i for p in posts if p.get("status") in ("publicado", "agendado") for i in p.get("produtos", [])}

    atual = [l for l in linhas if ini <= l["dia"] <= hoje]
    ant = [l for l in linhas if ini_ant <= l["dia"] <= fim_ant]
    soma = lambda ls, k: sum(l[k] for l in ls)

    out = [f"# Vendas: {ini:%d/%m/%Y} a {hoje:%d/%m/%Y} ({a.dias} dias)", ""]
    for e in erros[:10]:
        out.append(f"> Aviso: {e}")
    if erros:
        out.append("")
    if not atual:
        out.append("Sem vendas no período. Confira se o CSV tem linhas dessas datas "
                   "(Shopee: relatório sai às 10:30 do dia seguinte).")
        txt = "\n".join(out)
        print(txt)
        return 0

    c1, p1, c0, p0 = soma(atual, "comissao"), soma(atual, "pedidos"), soma(ant, "comissao"), soma(ant, "pedidos")
    var = f" ({(c1 - c0) / c0 * 100:+.0f}% em relação aos {a.dias} dias anteriores)" if c0 else " (sem período anterior para comparar)"
    out += [f"**Comissão:** {brl(c1)}{var}", f"**Pedidos:** {p1}" + (f" (antes: {p0})" if ant else ""), ""]

    por_loja = {}
    for l in atual:
        d = por_loja.setdefault(l["loja"], [0, 0.0])
        d[0] += l["pedidos"]
        d[1] += l["comissao"]
    out += ["## Por loja", "| Loja | Pedidos | Comissão |", "|---|--:|--:|"]
    for k, (p, c) in sorted(por_loja.items(), key=lambda x: -x[1][1]):
        out.append(f"| {LOJAS[k]} | {p} | {brl(c)} |")

    por_prod = {}
    for l in atual:
        d = por_prod.setdefault((l["loja"], l["produto"]), [0, 0.0])
        d[0] += l["pedidos"]
        d[1] += l["comissao"]
    rank = sorted(por_prod.items(), key=lambda x: (-x[1][1], -x[1][0]))
    out += ["", "## Top produtos", "| # | Produto | Loja | Pedidos | Comissão | No catálogo |", "|--:|---|---|--:|--:|---|"]
    casados = []
    for n, ((loja, prod), (p, c)) in enumerate(rank[:10], 1):
        it, r = casar(prod, loja, itens)
        casados.append((it, loja, prod, c))
        status = "—"
        if it:
            status = ("já postado/agendado" if it["id"] in postados else "nunca postado")
        out.append(f"| {n} | {prod[:60]} | {LOJAS[loja]} | {p} | {brl(c)} | {status} |")

    # Repetir: itens que venderam + irmãos da mesma categoria/loja ainda não postados
    out += ["", "## O que repetir"]
    sug, vistos = [], set()
    for it, loja, prod, c in casados[:5]:
        if not it:
            sug.append(f"- **{prod[:60]}** ({LOJAS[loja]}) vendeu mas não está no catálogo: "
                       "adicionar em `dados/itens.json` se ainda está à venda.")
            continue
        if it["id"] not in postados:
            sug.append(f"- **{it['nome'].replace('&amp;', '&')}** vendeu e **nunca foi postado**: "
                       "faz um post/Story dele.")
        else:
            sug.append(f"- **{it['nome'].replace('&amp;', '&')}** vendeu: repostar com outro ângulo "
                       "(Story ou Reel) na próxima semana.")
        irmaos = [x for x in itens if x["loja"] == it["loja"] and x["cat"] == it["cat"]
                  and x["id"] != it["id"] and x["id"] not in postados and x["id"] not in vistos]
        irmaos.sort(key=lambda x: x.get("conferido", ""), reverse=True)
        for x in irmaos[:2]:
            vistos.add(x["id"])
            sug.append(f"  - parecido, ainda não postado ({it['cat']}): {x['nome'].replace('&amp;', '&')} — {x.get('preco', '?')}")
    out += sug or ["- Nada a sugerir."]
    out += ["", "_Relatório interno: não publicar. Comissão fica só aqui, nunca no Telegram nem no repositório._"]

    txt = "\n".join(out)
    print(txt)
    if a.saida:
        with open(dest, "w", encoding="utf-8") as f:
            f.write(txt + "\n")
        print(f"\n(salvo em {dest})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

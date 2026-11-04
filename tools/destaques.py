#!/usr/bin/env python3
"""Robô de Destaques: separa os Stories publicados nas áreas dos destaques do perfil.

A API do Instagram não cria nem edita destaques (só pelo app). Este robô faz o que
dá para automatizar: classifica cada Story por área e grava dados/destaques.json,
que a aba "Destaques" do painel mostra com miniaturas e uma lista do que falta
adicionar. Áreas (as mesmas bolinhas do perfil): OFERTAS, TECH, MODA, BELEZA, COZINHA, CASA.
Uso: python3 -I tools/destaques.py
"""
import datetime
import json
import os
import re
import sys
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AREAS = ["OFERTAS", "TECH", "MODA", "BELEZA", "COZINHA", "CASA"]

TECH = r"fone|carregador|cabo |smartwatch|relogio inteligente|celular|smartphone|mouse|teclado|camera|bluetooth|caixa de som|jbl|power bank|powerbank|tablet|notebook|tv box|webcam|headset|ring light|lanterna|compressor|eletronic|usb|wifi|alexa"
COZINHA = r"cozinha|panela|frigideira|air ?fryer|fritadeira|cafeteira|copo|garrafa|faca|tabua|utensil|pote|forma |liquidificador|mixer|escorredor|marmita|tempero|assadeira|xicara|chaleira|batedeira|sanduicheira|tigela|talher|prato|peneira|ralador|descascador"


def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s.replace("&amp;", " "))


def area_do_item(it):
    cat, nome = norm(it.get("cat")), norm(it.get("nome"))
    if "beleza" in cat:
        return "BELEZA"
    if "mercado" in cat:
        return "COZINHA"
    if "casa e cozinha" in cat:
        return "COZINHA" if re.search(COZINHA, nome) else "CASA"
    if "moda" in cat or "eletron" in cat:
        return "TECH" if re.search(TECH, nome) else "MODA"
    if re.search(TECH, nome):
        return "TECH"
    return "CASA"  # Pet, Ferramentas e garagem, Infantil e brinquedos


def areas_do_post(p, itens):
    """Lista de áreas: queda de preço vai para OFERTAS e também para a área do produto; Story do site, só OFERTAS."""
    if p.get("area"):
        return [p["area"]]
    ids = p.get("produtos") or []
    it = itens.get(ids[0]) if ids else None
    if not it:
        return ["OFERTAS"]
    a = area_do_item(it)
    queda = "queda de" in norm(p.get("legenda")) or "caiu" in norm(p.get("tema"))
    return ["OFERTAS", a] if queda and a != "OFERTAS" else [a]


def main():
    J = lambda *a: os.path.join(RAIZ, *a)
    itens = json.load(open(J("dados", "itens.json"), encoding="utf-8"))
    itens = {i["id"]: i for i in (itens if isinstance(itens, list) else itens.get("itens", []))}
    posts = json.load(open(J("dados", "posts.json"), encoding="utf-8"))
    por = {a: [] for a in AREAS}
    for p in posts:
        if p.get("formato") != "story":
            continue
        for a in areas_do_post(p, itens):
            por[a].append({
                "id": p["id"], "data": p["data"], "hora": p.get("hora"), "tema": re.sub(r"^Story: ", "", p.get("tema", "")),
                "status": p.get("status"), "publicado_em": p.get("publicado_em"),
                "img": (p.get("imagens") or [""])[0]})
    for a in AREAS:
        por[a].sort(key=lambda x: (x["data"], x["hora"] or ""), reverse=True)
    res = {
        "atualizado": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).strftime("%Y-%m-%d %H:%M"),
        "areas": [{"nome": a, "stories": por[a]} for a in AREAS],
        "como": "Instagram > Perfil > menu (três linhas) > Arquivo > Arquivo de Stories > abrir o Story > Destacar > escolher a área.",
        "aviso": "A API do Instagram não cria destaques; este arquivo só organiza os Stories por área.",
    }
    open(J("dados", "destaques.json"), "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    print("destaques.json:", ", ".join("%s %d" % (a, len(por[a])) for a in AREAS))
    return 0


if __name__ == "__main__":
    sys.exit(main())

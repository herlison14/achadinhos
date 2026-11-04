#!/usr/bin/env python3
"""Robô de Tendências: o que está chegando e o que é bom de postar.

Usa só dados nossos e calendário (sem rede): datas comerciais próximas com a
fase (esquenta, contagem, dia), categorias com mais quedas de preço reais e
categorias com mais ofertas conferidas. Grava dados/tendencias.json. Nada de
preço, desconto ou fato inventado: a tarefa semanal usa isto como pauta.
Uso: python3 -I tools/tendencias.py [--hoje AAAA-MM-DD] [--mostrar]
"""
import json
import os
import sys
from collections import Counter
from datetime import date, timedelta

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(RAIZ, "dados")


def nth_weekday(ano, mes, dia_semana, n):
    d = date(ano, mes, 1)
    d += timedelta(days=(dia_semana - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def pascoa(ano):  # algoritmo de Gauss/Meeus (calendário gregoriano)
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(ano, mes, dia)


def datas(ano):
    bf = nth_weekday(ano, 11, 4, 4)  # 4ª sexta de novembro
    return [
        ("Dia do Consumidor", date(ano, 3, 15), "comparar preço e conferir antes de comprar"),
        ("Páscoa", pascoa(ano), "chocolate, cesta, decoração, presente"),
        ("Dia das Mães", nth_weekday(ano, 5, 6, 2), "presentes para mães, casa e beleza"),
        ("Dia dos Namorados", date(ano, 6, 12), "presentes até um valor, beleza, moda"),
        ("Dia dos Pais", nth_weekday(ano, 8, 6, 2), "ferramentas, eletrônicos, moda masculina"),
        ("Dia das Crianças", date(ano, 10, 12), "brinquedos e infantil"),
        ("11.11", date(ano, 11, 11), "data de promoção das lojas: conferir preço real antes"),
        ("Black Friday", bf, "preço inflado antes, como comparar com o histórico"),
        ("Cyber Monday", bf + timedelta(days=3), "tecnologia e eletrônicos"),
        ("Natal", date(ano, 12, 25), "presentes, decoração, ceia, amigo secreto"),
        ("Ano Novo", date(ano + 1, 1, 1), "organização, casa, virada, metas"),
    ]


def fase(dias):
    if dias < 0:
        return "passou"
    if dias == 0:
        return "dia"
    if dias <= 3:
        return "ultimos-dias"
    if dias <= 14:
        return "contagem"
    return "esquenta"


def main():
    hoje = date.today()
    if "--hoje" in sys.argv:
        hoje = date.fromisoformat(sys.argv[sys.argv.index("--hoje") + 1])
    prox = []
    for ano in (hoje.year, hoje.year + 1):
        for nome, d, ideia in datas(ano):
            dias = (d - hoje).days
            if 0 <= dias <= 75:
                prox.append({"nome": nome, "data": d.isoformat(), "dias": dias, "fase": fase(dias), "pauta": ideia})
    prox.sort(key=lambda x: x["dias"])
    vistos, unicos = set(), []
    for x in prox:  # evita duplicata do mesmo evento em dois anos
        if x["nome"] not in vistos:
            vistos.add(x["nome"]); unicos.append(x)

    itens = json.load(open(os.path.join(D, "itens.json"), encoding="utf-8"))
    itens = itens if isinstance(itens, list) else itens.get("itens", [])
    por_id = {i["id"]: i for i in itens}
    cat_ofertas = Counter(i.get("cat", "?") for i in itens)
    quedas = []
    try:
        quedas = json.load(open(os.path.join(D, "quedas.json"), encoding="utf-8"))
    except Exception:
        pass
    cat_quedas = Counter(por_id[q["id"]].get("cat", "?") for q in quedas if q.get("id") in por_id)
    res = {
        "gerado_em": hoje.isoformat(),
        "datas_proximas": unicos,
        "categorias_com_quedas": [{"categoria": c, "quedas": n} for c, n in cat_quedas.most_common(5)],
        "categorias_com_mais_ofertas": [{"categoria": c, "itens": n} for c, n in cat_ofertas.most_common(5)],
        "aviso": "Pauta de calendário e de dados do site. Não contém preço nem promessa de desconto.",
    }
    texto = json.dumps(res, ensure_ascii=False, indent=1)
    if "--mostrar" in sys.argv:
        print(texto)
    else:
        open(os.path.join(D, "tendencias.json"), "w", encoding="utf-8").write(texto + "\n")
        print("tendencias.json gravado")
        for x in unicos[:5]:
            print("-", x["nome"], x["data"], "em", x["dias"], "dias (" + x["fase"] + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())

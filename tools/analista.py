#!/usr/bin/env python3
"""Robô Analista: lê dados/metricas.json (só números de desempenho) e grava
dados/estrategia.json com o que mais rende por formato, objetivo e horário.

Nada de segredo, comissão ou ganho aqui. As tarefas semanais (crescimento e
Reels) leem o resultado para decidir o que repetir.
Uso: python3 -I tools/analista.py            (grava dados/estrategia.json)
     python3 -I tools/analista.py --mostrar  (só imprime)
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MET = os.path.join(RAIZ, "dados", "metricas.json")
SAIDA = os.path.join(RAIZ, "dados", "estrategia.json")
MIN_AMOSTRA = 3  # abaixo disso o grupo é "pouca amostra" e não manda no plano


def pontos(p):
    """Nota de um post: alcance pesa 1, salvar e enviar valem muito mais
    (são os sinais que a Meta mais recompensa), comentário e curtida pouco."""
    return (p.get("reach") or 0) + 8 * (p.get("saved") or 0) + 8 * (p.get("shares") or 0) \
        + 3 * (p.get("comentarios") or 0) + 1 * (p.get("curtidas") or 0)


def grupo(posts, chave):
    g = defaultdict(list)
    for p in posts:
        g[p.get(chave) or "?"].append(p)
    out = []
    for k, v in g.items():
        n = len(v)
        out.append({
            "nome": k, "posts": n,
            "alcance_medio": round(sum(x.get("reach") or 0 for x in v) / n, 1),
            "views_medio": round(sum(x.get("views") or 0 for x in v) / n, 1),
            "nota_media": round(sum(pontos(x) for x in v) / n, 1),
            "confiavel": n >= MIN_AMOSTRA,
        })
    out.sort(key=lambda x: (-x["confiavel"], -x["nota_media"]))
    return out


def main():
    if not os.path.exists(MET):
        print("sem dados/metricas.json ainda")
        return 0
    m = json.load(open(MET, encoding="utf-8"))
    posts = [p for p in m.get("posts", []) if p.get("reach") is not None]
    dias = m.get("dias", [])
    res = {
        "atualizado": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "posts_analisados": len(posts),
        "por_formato": grupo(posts, "formato"),
        "por_objetivo": grupo(posts, "objetivo"),
        "por_hora": grupo(posts, "hora"),
        "melhores_posts": [
            {"id": p["id"], "formato": p.get("formato"), "objetivo": p.get("objetivo"),
             "hora": p.get("hora"), "alcance": p.get("reach"), "nota": pontos(p)}
            for p in sorted(posts, key=pontos, reverse=True)[:5]],
    }
    if len(dias) >= 2:
        a, b = dias[-2], dias[-1]
        res["seguidores"] = {"hoje": b.get("seguidores"), "ontem": a.get("seguidores"),
                             "variacao_dia": (b.get("seguidores") or 0) - (a.get("seguidores") or 0)}
    if len(dias) >= 8:
        res["seguidores"]["variacao_7_dias"] = (dias[-1].get("seguidores") or 0) - (dias[-8].get("seguidores") or 0)

    dicas = []
    for rotulo, chave in (("formato", "por_formato"), ("objetivo", "por_objetivo"), ("horário", "por_hora")):
        conf = [x for x in res[chave] if x["confiavel"]]
        if conf:
            dicas.append("Melhor %s até agora: %s (nota média %s em %d posts)."
                         % (rotulo, conf[0]["nome"], conf[0]["nota_media"], conf[0]["posts"]))
    fracos = [x for x in res["por_formato"] if x["confiavel"] and x["nota_media"] == 0]
    for x in fracos:
        dicas.append("Formato %s sem nenhum sinal ainda: testar gancho/capa diferente antes de repetir." % x["nome"])
    if not dicas:
        dicas.append("Poucos posts por grupo (menos de %d): continuar variando formato, objetivo e horário para gerar amostra." % MIN_AMOSTRA)
    sem_sinal = sum(1 for p in posts if (p.get("saved") or 0) + (p.get("shares") or 0) == 0)
    if posts and sem_sinal == len(posts):
        dicas.append("Nenhum post teve salvamento ou envio ainda: priorizar conteúdo que vale guardar (listas, comparativos, calendário de datas) e CTA claro de salvar/enviar.")
    res["dicas"] = dicas
    res["aviso"] = "Amostra pequena: tratar como pista, não como regra. Só números de desempenho, sem comissão."

    texto = json.dumps(res, ensure_ascii=False, indent=1)
    if "--mostrar" in sys.argv:
        print(texto)
    else:
        with open(SAIDA, "w", encoding="utf-8") as f:
            f.write(texto + "\n")
        print("estrategia.json gravado (%d posts)" % len(posts))
        for d in dicas:
            print("-", d)
    return 0


if __name__ == "__main__":
    sys.exit(main())

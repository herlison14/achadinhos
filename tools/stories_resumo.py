"""Resumo das métricas dos Stories (só números): lê dados/stories_metricas.json, gravado por
`tools/instagram.py stories`, e acrescenta a chave "resumo" com médias por dia, horário, área e tipo.
Serve para avaliar o teste de 10 Stories/dia (16 a 22/11/2026): views por Story x views totais por dia
e quanta gente sai no meio (toque em "sair"). Amostra pequena = pista, não conclusão."""
import json
from collections import defaultdict
from pathlib import Path

ARQ = Path(__file__).resolve().parent.parent / "dados" / "stories_metricas.json"


def num(v):
    return v if isinstance(v, (int, float)) else None


def media(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 1) if xs else None


def grupo(regs, chave):
    g = defaultdict(list)
    for r in regs:
        g[chave(r)].append(r)
    out = []
    for k, rs in g.items():
        out.append({"nome": k, "stories": len(rs), "views_medio": media([num(r.get("views")) for r in rs]),
                    "alcance_medio": media([num(r.get("reach")) for r in rs]),
                    "views_total": sum(num(r.get("views")) or 0 for r in rs),
                    "respostas": sum(num(r.get("replies")) or 0 for r in rs),
                    "visitas_perfil": sum(num(r.get("profile_visits")) or 0 for r in rs),
                    "saidas_pct": taxa_saida(rs)})
    return out


def taxa_saida(rs):
    saidas = views = 0
    for r in rs:
        nav, v = r.get("navegacao") or {}, num(r.get("views"))
        if v and "tap_exit" in nav:
            saidas += nav["tap_exit"]
            views += v
    return round(100 * saidas / views, 1) if views else None


def main():
    if not ARQ.exists():
        print("ainda sem dados/stories_metricas.json")
        return
    d = json.loads(ARQ.read_text(encoding="utf-8"))
    regs = list(d.get("stories", {}).values())
    finais = [r for r in regs if (r.get("horas_no_ar") or 0) >= 18]   # leitura perto do fim das 24 h
    por_dia = sorted(grupo(finais, lambda r: r["publicado_em"][:10]), key=lambda x: x["nome"])
    d["resumo"] = {
        "stories_com_leitura_final": len(finais),
        "por_dia": por_dia,
        "por_hora": sorted(grupo(finais, lambda r: r.get("hora") or "?"), key=lambda x: x["nome"]),
        "por_area": sorted(grupo(finais, lambda r: r.get("area") or "?"), key=lambda x: -(x["views_medio"] or 0)),
        "por_tipo": sorted(grupo(finais, lambda r: r.get("tipo") or "?"), key=lambda x: -(x["views_medio"] or 0)),
        "menos_de_5": sum(1 for r in finais if r.get("views") == "menos de 5"),
    }
    ARQ.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("Stories com leitura final (18 h ou mais no ar): %d" % len(finais))
    for x in por_dia:
        print("%s  %2d Stories  views/Story %-6s  views no dia %-5s  saídas %s%%" % (
            x["nome"], x["stories"], x["views_medio"], x["views_total"], x["saidas_pct"]))


if __name__ == "__main__":
    main()

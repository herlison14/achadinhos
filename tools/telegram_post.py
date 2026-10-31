#!/usr/bin/env python3
"""Espelha no canal do Telegram os carrosséis que o robô acabou de publicar no Instagram (mesma execução, mesmo horário).

Para cada post de dados/posts.json com canal "ig", status "publicado", publicado_em a partir de 31/10/2026 e sem o campo
"telegram_em": envia as imagens (álbum) com o título e, em seguida, uma mensagem com cada produto, preço, data de conferência
e o link de afiliado (no Telegram o link vai direto, ao contrário do Instagram). Depois grava "telegram_em" no post.

Variáveis de ambiente (segredos do GitHub): TELEGRAM_TOKEN; TELEGRAM_CHAT (padrão @achadinhosdobinga).
  python3 tools/telegram_post.py           envia o que estiver pendente
  python3 tools/telegram_post.py --seco    só mostra o que enviaria
"""
import html, json, os, sys, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
POSTS = RAIZ / "dados" / "posts.json"
ITENS = RAIZ / "dados" / "itens.json"
RAW = "https://raw.githubusercontent.com/herlison14/achadinhos/main/"
SITE = "https://achadinhosdobinga.com.br"
LOJAS = {"shopee": "Shopee", "amazon": "Amazon", "meli": "Mercado Livre", "aliexpress": "AliExpress", "magalu": "Magalu"}
BRT = timezone(timedelta(hours=-3))
DESDE = "2026-10-31 00:00"      # não reenvia posts antigos
JANELA_H = 36                    # só posts publicados nas últimas 36 h


def ler(p):
    return json.loads(p.read_text(encoding="utf-8"))


def br(iso):
    a, m, d = iso.split("-")
    return f"{d}/{m}/{a}"


def chamar(metodo, dados):
    tok = os.environ["TELEGRAM_TOKEN"]
    corpo = urllib.parse.urlencode(dados).encode()
    try:
        r = urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/{metodo}", corpo, timeout=60)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read()).get("description", "")
        except Exception:
            msg = ""
        raise RuntimeError("HTTP %d %s" % (e.code, msg.replace(tok, "***")))


def titulo(post):
    # primeira linha da legenda sem o resumo de faixa de preço colado no fim
    return (post.get("legenda") or post.get("tema") or "").strip().splitlines()[0]


def texto_produtos(post, itens):
    linhas, datas, amazon = [], [], False
    for pid in post.get("produtos", []):
        i = itens.get(pid)
        if not i:
            continue
        amazon = amazon or i["loja"] == "amazon"
        datas.append(i["conferido"])
        nome = html.unescape(i["nome"])
        linhas.append(f"• {nome}\n  R$ {i['preco']} na {LOJAS.get(i['loja'], i['loja'])}\n  {i['href']}")
    if not linhas:
        return None
    rodape = ["", "Preços conferidos em %s. Podem mudar: vale o preço da loja." % br(min(datas)),
              "Mais ofertas: %s/?o=tg" % SITE, "", "Publicidade: links de afiliado."]
    if amazon:
        rodape.append("Como Associado da Amazon, posso receber comissão pelas compras qualificadas.")
    return "\n".join(linhas + rodape)


def main(seco):
    posts, itens = ler(POSTS), {i["id"]: i for i in ler(ITENS)}
    agora = datetime.now(BRT)
    mudou = False
    for p in posts:
        pub = p.get("publicado_em")
        if p.get("canal") != "ig" or p.get("status") != "publicado" or p.get("telegram_em") or not pub or not p.get("imagens"):
            continue
        quando = datetime.strptime(pub, "%Y-%m-%d %H:%M").replace(tzinfo=BRT)
        if pub < DESDE or (agora - quando).total_seconds() > JANELA_H * 3600:
            continue
        texto = texto_produtos(p, itens)
        if not texto:
            continue
        midias = [{"type": "photo", "media": RAW + im} for im in p["imagens"][:10]]
        midias[0]["caption"] = titulo(p)[:1000]
        if seco:
            print("[seco]", p["id"], len(midias), "imagens;", titulo(p))
            print(texto)
            continue
        try:
            chamar("sendMediaGroup", {"chat_id": os.environ.get("TELEGRAM_CHAT", "@achadinhosdobinga"), "media": json.dumps(midias)})
            chamar("sendMessage", {"chat_id": os.environ.get("TELEGRAM_CHAT", "@achadinhosdobinga"), "text": texto,
                                   "disable_web_page_preview": "true"})
            p["telegram_em"] = agora.strftime("%Y-%m-%d %H:%M")
            mudou = True
            print("Telegram: enviado", p["id"])
        except (RuntimeError, urllib.error.URLError) as e:
            print("::error::Telegram não recebeu %s: %s" % (p["id"], str(e)[:200]))
    if mudou:
        POSTS.write_text(json.dumps(posts, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    seco = "--seco" in sys.argv
    if not seco and not os.environ.get("TELEGRAM_TOKEN"):
        print("TELEGRAM_TOKEN não configurado: nada a fazer.")
        sys.exit(0)
    sys.exit(main(seco))

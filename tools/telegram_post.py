#!/usr/bin/env python3
"""Espelha no canal do Telegram os carrosséis que o robô acabou de publicar no Instagram (mesma execução, mesmo horário).

Para cada post de dados/posts.json com canal "ig", status "publicado", publicado_em a partir de 31/10/2026 e sem o campo
"telegram_em": envia as imagens (álbum) com o título e, em seguida, uma mensagem com cada produto, preço, data de conferência
e o link de afiliado (no Telegram o link vai direto, ao contrário do Instagram). Depois grava "telegram_em" no post.

Variáveis de ambiente (segredos do GitHub): TELEGRAM_TOKEN; TELEGRAM_CHAT (padrão @achadinhosdobinga).
  python3 tools/telegram_post.py           envia o que estiver pendente
  python3 tools/telegram_post.py --seco    só mostra o que enviaria
  python3 tools/telegram_post.py --id ID   espelha só esse post, mesmo fora da janela de 36 h (fluxo "Canal do
                                           Telegram", tipo "espelho"); recusa se algum preço tiver mais de 7 dias ou
                                           não bater com a legenda

Se o Telegram não conseguir baixar alguma imagem pelo link do GitHub (ex.: "WEBPAGE_CURL_FAILED", que ele guarda em
cache e repete em toda tentativa), o álbum é reenviado com as imagens anexadas direto do repositório.
"""
import html, json, os, sys, uuid, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
POSTS = RAIZ / "dados" / "posts.json"
ITENS = RAIZ / "dados" / "itens.json"
RAW = "https://raw.githubusercontent.com/herlison14/achadinhos/main/"
SITE = "https://achadinhosdobinga.com.br"
LOJAS = {"shopee": "Shopee", "amazon": "Amazon", "meli": "Mercado Livre", "aliexpress": "AliExpress", "magalu": "Magalu",
         "kabum": "KaBuM!", "nike": "Nike", "dafiti": "Dafiti", "adidas": "adidas", "docebeleza": "Doce Beleza", "puma": "PUMA", "hope": "Hope Lingerie", "havaianas": "Havaianas", "cea": "C&A", "reserva": "Reserva", "lauri": "Lauri Esporte", "mizuno": "Mizuno", "polishop": "Polishop"}
BRT = timezone(timedelta(hours=-3))
DESDE = "2026-10-31 00:00"      # não reenvia posts antigos
JANELA_H = 36                    # só posts publicados nas últimas 36 h
MAX_DIAS_PRECO = 7               # --id: preço conferido há no máximo 7 dias (mesma trava do Instagram)
ERROS_URL = ("WEBPAGE_CURL_FAILED", "WEBPAGE_MEDIA_EMPTY", "failed to get HTTP URL content", "wrong file identifier")


def ler(p):
    return json.loads(p.read_text(encoding="utf-8"))


def br(iso):
    a, m, d = iso.split("-")
    return f"{d}/{m}/{a}"


def chamar(metodo, dados, arquivos=None):
    tok = os.environ["TELEGRAM_TOKEN"]
    cab = {}
    if arquivos:   # multipart: arquivos = {nome: (arquivo.jpg, bytes)}
        sep = uuid.uuid4().hex
        partes = []
        for k, v in dados.items():
            partes.append(f'--{sep}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        for k, (nome, conteudo) in arquivos.items():
            partes.append(f'--{sep}\r\nContent-Disposition: form-data; name="{k}"; filename="{nome}"\r\n'
                          f'Content-Type: image/jpeg\r\n\r\n'.encode() + conteudo + b"\r\n")
        corpo = b"".join(partes) + f"--{sep}--\r\n".encode()
        cab["Content-Type"] = "multipart/form-data; boundary=" + sep
    else:
        corpo = urllib.parse.urlencode(dados).encode()
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/{metodo}", corpo, cab)
        r = urllib.request.urlopen(req, timeout=120)
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
        if not i or i["loja"] == "adidas":   # termos da adidas (Awin) não autorizam Telegram
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


def enviar_album(chat, p, midias):
    """Envia o álbum pelo link do GitHub; se o Telegram não baixar alguma imagem, anexa os arquivos do repositório."""
    try:
        chamar("sendMediaGroup", {"chat_id": chat, "media": json.dumps(midias)})
        return
    except RuntimeError as e:
        if not any(x in str(e) for x in ERROS_URL):
            raise
        print("AVISO: Telegram não baixou imagem de %s pelo link (%s); reenviando com as imagens anexadas." % (p["id"], str(e)[:120]))
    arquivos, anexadas = {}, []
    for n, (m, im) in enumerate(zip(midias, p["imagens"][:10])):
        arq = RAIZ / im
        if not arq.is_file():
            raise RuntimeError("imagem %s não existe no repositório" % im)
        arquivos["f%d" % n] = (arq.name, arq.read_bytes())
        anexadas.append(dict(m, media="attach://f%d" % n))
    chamar("sendMediaGroup", {"chat_id": chat, "media": json.dumps(anexadas)}, arquivos)


def problemas_forcado(p, itens, agora):
    """--id: mesma prudência do Instagram (preço recente e igual ao da legenda)."""
    erros, leg = [], p.get("legenda") or ""
    if p.get("canal") != "ig" or p.get("status") != "publicado" or not p.get("imagens") or p.get("formato") == "story":
        erros.append("só carrossel/post de feed já publicado no Instagram")
    if p.get("telegram_em"):
        erros.append("já espelhado em %s" % p["telegram_em"])
    for pid in p.get("produtos", []):
        i = itens.get(pid)
        if not i:
            erros.append("produto %s não está mais em itens.json" % pid)
            continue
        dias = (agora.date() - datetime.strptime(i["conferido"], "%Y-%m-%d").date()).days
        if dias > MAX_DIAS_PRECO:
            erros.append("preço de %s conferido há %d dias" % (pid, dias))
        if not p.get("sem_preco") and "R$ %s" % i["preco"] not in leg:
            erros.append("preço atual de %s (R$ %s) não bate com o card/legenda" % (pid, i["preco"]))
    return erros


def main(seco, so_id=None):
    posts, itens = ler(POSTS), {i["id"]: i for i in ler(ITENS)}
    agora = datetime.now(BRT)
    mudou = False
    if so_id and not any(p.get("id") == so_id for p in posts):
        print("::error::post %s não existe em dados/posts.json" % so_id)
        return 1
    for p in posts:
        pub = p.get("publicado_em")
        if so_id:
            if p.get("id") != so_id:
                continue
            erros = problemas_forcado(p, itens, agora)
            if erros:
                print("::error::Não espelhei %s: %s" % (so_id, "; ".join(erros)))
                return 1
        else:
            if p.get("canal") != "ig" or p.get("status") != "publicado" or p.get("telegram_em") or not pub or not p.get("imagens") or p.get("formato") == "story":   # Story não vai para o canal
                continue
            quando = datetime.strptime(pub, "%Y-%m-%d %H:%M").replace(tzinfo=BRT)
            if pub < DESDE or (agora - quando).total_seconds() > JANELA_H * 3600:
                continue
        texto = texto_produtos(p, itens)
        if not texto and p.get("sem_preco"):   # post de crescimento: sem produtos, só o convite para o site
            texto = "Mais ofertas com preço conferido: %s/?o=tg\n\nPublicidade: links de afiliado." % SITE
        if not texto:
            continue
        midias = [{"type": "photo", "media": RAW + im} for im in p["imagens"][:10]]
        midias[0]["caption"] = titulo(p)[:1000]
        if seco:
            print("[seco]", p["id"], len(midias), "imagens;", titulo(p))
            print(texto)
            continue
        try:
            enviar_album(os.environ.get("TELEGRAM_CHAT", "@achadinhosdobinga"), p, midias)
            chamar("sendMessage", {"chat_id": os.environ.get("TELEGRAM_CHAT", "@achadinhosdobinga"), "text": texto,
                                   "disable_web_page_preview": "true"})
            p["telegram_em"] = agora.strftime("%Y-%m-%d %H:%M")
            mudou = True
            print("Telegram: enviado", p["id"])
        except (RuntimeError, urllib.error.URLError) as e:
            print("::error::Telegram não recebeu %s: %s" % (p["id"], str(e)[:200]))
            if so_id:
                return 1
    if mudou:
        POSTS.write_text(json.dumps(posts, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    seco = "--seco" in sys.argv
    so_id = sys.argv[sys.argv.index("--id") + 1].strip() if "--id" in sys.argv[:-1] else None
    if not seco and not os.environ.get("TELEGRAM_TOKEN"):
        print("TELEGRAM_TOKEN não configurado: nada a fazer.")
        sys.exit(1 if so_id else 0)
    sys.exit(main(seco, so_id))

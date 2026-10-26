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
import base64, html, io, json, os, re, sys, urllib.request, urllib.parse, uuid
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



FONTES = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
          "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf"]


def fonte(tam):
    from PIL import ImageFont
    for f in FONTES:
        try:
            return ImageFont.truetype(f, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def foto_do_item(i):
    """Devolve a foto do item como imagem PIL, ou None se não conseguir baixar."""
    from PIL import Image
    img = i.get("img", "")
    try:
        if img.startswith("data:"):
            return Image.open(io.BytesIO(base64.b64decode(img.split(",", 1)[1]))).convert("RGB")
        urls = [img]
        if "aliexpress-media.com" in img:
            urls.insert(0, re.sub(r"_\d+x\d+\.(jpg|png)$", "", img))
        if "/280x210/" in img:
            urls.insert(0, img.replace("/280x210/", "/600x450/"))
        for u in urls:
            try:
                req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
                return Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=20).read())).convert("RGB")
            except Exception:
                continue
    except Exception:
        pass
    return None


def quebrar(draw, texto, fnt, largura, max_linhas):
    palavras, linhas, atual = texto.split(), [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if draw.textlength(teste, font=fnt) <= largura:
            atual = teste
        else:
            linhas.append(atual)
            atual = p
    linhas.append(atual)
    if len(linhas) > max_linhas:
        linhas = linhas[:max_linhas]
        while draw.textlength(linhas[-1] + "…", font=fnt) > largura:
            linhas[-1] = linhas[-1][:-1]
        linhas[-1] += "…"
    return linhas


def preco_texto(i):
    pre = re.sub(r"<[^>]+>", "", i.get("pre", "") or "").strip()
    pos = re.sub(r"<[^>]+>", "", i.get("pos", "") or "").strip()
    return pre, "R$ " + i["preco"], pos


def cartao(i):
    """Cartão 1080x1080 no padrão visual da marca. Devolve bytes PNG."""
    from PIL import Image, ImageDraw
    W = 1080
    img = Image.new("RGB", (W, W), "#F4F0FF")
    d = ImageDraw.Draw(img)
    roxo, amarelo, vermelho = "#291258", "#FFC93B", "#DC3C46"
    try:                                           # logo e nome da marca
        logo = Image.open(RAIZ / "tools" / "logo.png").convert("RGBA").resize((110, 110))
        img.paste(logo, (60, 40), logo)
    except Exception:
        pass
    d.text((190, 72), "Achadinhos do Binga", font=fonte(40), fill=roxo)
    loja = LOJAS.get(i["loja"], i["loja"])
    f_l = fonte(30)
    w = int(d.textlength(loja, font=f_l)) + 56
    d.rounded_rectangle((W - 60 - w, 66, W - 60, 124), 29, fill=roxo)
    d.text((W - 60 - w + 28, 77), loja, font=f_l, fill=amarelo)
    d.rounded_rectangle((90, 190, W - 90, 700), 36, fill="white")   # quadro da foto
    foto = foto_do_item(i)
    if foto:
        foto.thumbnail((W - 260, 440), Image.LANCZOS)
        if foto.width < 360 and foto.height < 360:                  # miniaturas pequenas: amplia com suavidade
            k = min(420 / foto.width, 420 / foto.height)
            foto = foto.resize((int(foto.width * k), int(foto.height * k)), Image.LANCZOS)
        img.paste(foto, ((W - foto.width) // 2, 190 + (510 - foto.height) // 2))
    else:                                           # sem foto: logo grande no quadro, nunca um quadro vazio
        try:
            g = Image.open(RAIZ / "tools" / "logo.png").convert("RGBA").resize((300, 300))
            img.paste(g, ((W - 300) // 2, 190 + (510 - 300) // 2), g)
        except Exception:
            pass
    nome = html.unescape(i["nome"])
    y = 735
    for linha in quebrar(d, nome, fonte(44), W - 160, 2):
        d.text((80, y), linha, font=fonte(44), fill=roxo)
        y += 56
    pre, preco, pos = preco_texto(i)
    x = 80
    if pre:
        d.text((x, 880), pre, font=fonte(34), fill=vermelho)
        x += int(d.textlength(pre, font=fonte(34))) + 12
    d.text((x, 850), preco, font=fonte(100), fill=vermelho)
    if pos:
        x += int(d.textlength(preco, font=fonte(100))) + 18
        d.text((x, 900), pos, font=fonte(36), fill=roxo)
    d.rounded_rectangle((80, 985, 460, 1040), 28, fill=roxo)
    d.text((104, 996), "LINK NA LEGENDA", font=fonte(30), fill=amarelo)
    d.text((486, 1004), f"Conferido em {br(i['conferido'])} • pode mudar", font=fonte(24), fill=roxo)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def legenda(i):
    pre, preco, pos = preco_texto(i)
    p = (pre + " " if pre else "") + preco + (" " + pos if pos else "")
    return (f"{html.unescape(i['nome'])}\n{p} na {LOJAS.get(i['loja'], i['loja'])}\n"
            f"Conferido em {br(i['conferido'])}, pode mudar.\n\n{i['href']}")


def telegram_foto(png, legenda_txt):
    tok, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT")
    if not tok or not chat:
        sys.exit("Defina TELEGRAM_TOKEN e TELEGRAM_CHAT no ambiente (nunca no repositório).")
    lim = "----" + uuid.uuid4().hex
    corpo = b""
    for k, v in (("chat_id", chat), ("caption", legenda_txt)):
        corpo += f'--{lim}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    corpo += (f'--{lim}\r\nContent-Disposition: form-data; name="photo"; filename="oferta.png"\r\n'
              f'Content-Type: image/png\r\n\r\n').encode() + png + f"\r\n--{lim}--\r\n".encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendPhoto", corpo,
                                 {"Content-Type": f"multipart/form-data; boundary={lim}"})
    print("Telegram foto:", json.loads(urllib.request.urlopen(req, timeout=60).read()).get("ok"))



def cartao_boasvindas():
    """Cartão de apresentação do canal (logo, nome e promessa). Devolve bytes PNG."""
    from PIL import Image, ImageDraw
    W = 1080
    img = Image.new("RGB", (W, W), "#F4F0FF")
    d = ImageDraw.Draw(img)
    roxo, amarelo = "#291258", "#FFC93B"
    logo = Image.open(RAIZ / "tools" / "logo.png").convert("RGBA").resize((420, 420))
    img.paste(logo, ((W - 420) // 2, 120), logo)
    f1 = fonte(74)
    t = "Achadinhos do Binga"
    d.text(((W - d.textlength(t, font=f1)) / 2, 580), t, font=f1, fill=roxo)
    f2 = fonte(40)
    for k, linha in enumerate(["Achadinhos e ofertas conferidas", "Shopee • Amazon • Mercado Livre",
                               "AliExpress • Magalu"]):
        d.text(((W - d.textlength(linha, font=f2)) / 2, 690 + k * 56), linha, font=f2, fill=roxo)
    f3 = fonte(32)
    t = "SEMPRE COM A DATA DA CONFERÊNCIA"
    w = int(d.textlength(t, font=f3)) + 70
    d.rounded_rectangle(((W - w) // 2, 900, (W + w) // 2, 966), 33, fill=roxo)
    d.text(((W - d.textlength(t, font=f3)) / 2, 914), t, font=f3, fill=amarelo)
    f4 = fonte(26)
    t = "Publicidade: links de afiliado"
    d.text(((W - d.textlength(t, font=f4)) / 2, 1000), t, font=f4, fill=roxo)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def legenda_whatsapp(i):
    pre, preco, pos = preco_texto(i)
    p = (pre + " " if pre else "") + preco + (" " + pos if pos else "")
    return (f"*{html.unescape(i['nome'])}*\n{p} na {LOJAS.get(i['loja'], i['loja'])}\n"
            f"Conferido em {br(i['conferido'])}. Pode mudar.\n\n{i['href']}\n\n"
            f"Mais ofertas: {SITE}/?o=wa\n_{AVISO}_")


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
    texto = texto.replace("*", "")   # texto puro: evita erro de formatação com nomes de produto
    dados = urllib.parse.urlencode({"chat_id": chat, "text": texto,
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
        if a[1:2] == ["boasvindas"]:
            telegram(texto_boasvindas("tg"))
            return
        itens = escolher(int(arg(a, "-n", 4)))
        if not itens:
            print("Sem itens novos conferidos nos últimos 7 dias: nada enviado.")
            return
        for i in itens:
            telegram_foto(cartao(i), legenda(i))
        telegram(f"Mais ofertas organizadas por categoria: {SITE}/?o=tg\n\n{AVISO}")
        registrar(itens)
    elif cmd == "whatsapp-cartoes":            # cartões + legendas para colar no canal do WhatsApp (não registra)
        pasta = Path(arg(a, "--saida", "canal/whatsapp"))
        pasta.mkdir(parents=True, exist_ok=True)
        for velho in list(pasta.glob("*.png")) + list(pasta.glob("*.txt")):
            velho.unlink()
        itens = escolher(int(arg(a, "-n", 4)))
        (pasta / "00_boasvindas.png").write_bytes(cartao_boasvindas())
        (pasta / "00_boasvindas.txt").write_text(texto_boasvindas("wa") + "\n", encoding="utf-8")
        for n, i in enumerate(itens, 1):
            (pasta / f"{n:02d}_{i['loja']}_{i['id']}.png").write_bytes(cartao(i))
            (pasta / f"{n:02d}_{i['loja']}_{i['id']}.txt").write_text(legenda_whatsapp(i) + "\n", encoding="utf-8")
        print(f"{len(itens)} cartões de oferta + boas-vindas em {pasta}")
    elif cmd == "cartao":                      # teste local: grava PNG do item (id) em --saida
        it = next(x for x in ler(ITENS, []) if x["id"] == a[1])
        Path(arg(a, "--saida", f"cartao_{a[1]}.png")).write_bytes(cartao(it))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])

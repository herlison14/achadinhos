#!/usr/bin/env python3
"""Gera os cards (JPEG 1080x1350) dos carrosséis de dados/posts.json no padrão visual da marca.

Nome, preço e data de cada produto vêm da LEGENDA do post (linhas "N. Nome: R$ 00,00"), para o card
ficar sempre igual à legenda. Fotos: img/cards/<id>.jpg ou img/<id>.webp.
Uso: python3 -I tools/cards.py SAIDA ID_DO_POST [ID_DO_POST ...]   (fontes TTF em FONTES)
"""
import html, json, os, re, sys
from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTES = os.environ.get('FONTES', '/tmp/f')
W, H = 1080, 1350
ROXO, AMARELO, VERM, LAV, ROXO2 = '#291258', '#FFC93B', '#DC3C46', '#F4F0FF', '#5B4B8A'
LOJAS = {'shopee': ('Shopee', '#EE4D2D', '#FFFFFF'), 'amazon': ('Amazon', '#232F3E', '#FF9900'),
         'meli': ('Mercado Livre', '#FFE600', '#2D3277'), 'magalu': ('Magalu', '#0086FF', '#FFFFFF'),
         'aliexpress': ('AliExpress', '#E62E04', '#FFFFFF')}

def fonte(nome, tam):
    return ImageFont.truetype(os.path.join(FONTES, nome + '.ttf'), tam)
BALOO = lambda t: fonte('baloo-2-latin-700-normal', t)
NUN8 = lambda t: fonte('nunito-latin-800-normal', t)
NUN7 = lambda t: fonte('nunito-latin-700-normal', t)

def larg(d, txt, f): return d.textlength(txt, font=f)

def quebrar(d, txt, f, max_w, max_linhas):
    pal, linhas, atual = txt.split(), [], ''
    for p in pal:
        t = (atual + ' ' + p).strip()
        if larg(d, t, f) <= max_w: atual = t
        else: linhas.append(atual); atual = p
    linhas.append(atual)
    if len(linhas) > max_linhas:
        linhas = linhas[:max_linhas]
        while larg(d, linhas[-1] + '…', f) > max_w: linhas[-1] = linhas[-1].rsplit(' ', 1)[0]
        linhas[-1] += '…'
    return linhas

def pilula(d, xy, txt, f, bg, fg, pad=38):
    w = larg(d, txt, f) + 2 * pad
    x0, y0, x1, y1 = xy[0], xy[1], xy[0] + w, xy[1] + 80
    d.rounded_rectangle((x0, y0, x1, y1), radius=40, fill=bg)
    d.text(((x0 + x1) / 2, (y0 + y1) / 2 + 2), txt, font=f, fill=fg, anchor='mm')
    return w

def logo(img, d):
    m = Image.open(os.path.join(RAIZ, 'img', 'marca.webp')).convert('RGB').resize((76, 76), Image.LANCZOS)
    mask = Image.new('L', (76, 76), 0); ImageDraw.Draw(mask).ellipse((0, 0, 75, 75), fill=255)
    img.paste(m, (76, 50), mask)
    d.text((166, 64), 'achadinhos', font=BALOO(34), fill=ROXO)
    d.text((166, 92), 'do binga', font=BALOO(34), fill=VERM)

def etiqueta(d, loja):
    nome, bg, fg = LOJAS[loja]
    f = NUN8(34); w = larg(d, nome, f) + 56
    d.rounded_rectangle((W - 60 - w, 52, W - 60, 118), radius=33, fill=bg)
    d.text((W - 60 - w / 2, 86), nome, font=f, fill=fg, anchor='mm')

def novo():
    img = Image.new('RGB', (W, H), LAV); return img, ImageDraw.Draw(img)

def foto(pid):
    for c in (os.path.join(RAIZ, 'img', 'cards', pid + '.jpg'), os.path.join(RAIZ, 'img', pid + '.webp')):
        if os.path.exists(c): return Image.open(c).convert('RGB')
    raise SystemExit('sem foto para ' + pid)

def encaixar(im, lado, pad):
    im = im.copy(); im.thumbnail((lado - 2 * pad, lado - 2 * pad), Image.LANCZOS)
    q = Image.new('RGB', (lado, lado), 'white')
    q.paste(im, ((lado - im.width) // 2, (lado - im.height) // 2)); return q

def arred(im, r):
    m = Image.new('L', im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=r, fill=255)
    out = Image.new('RGBA', im.size); out.paste(im, (0, 0)); out.putalpha(m); return out

def limpar(t): return re.sub(r'\s+', ' ', re.sub(r'[^\w\sçãõáéíóúâêôàÇÃÕÁÉÍÓÚÂÊÔÀ$.,:;!?()%/&+\-–|\'’"]', '', t)).strip()

def ler(post, itens):
    leg = post['legenda'].split('\n')
    data = re.search(r'em (\d\d/\d\d/\d{4})', post['legenda']).group(1)
    prods = []
    for l in leg:
        m = re.match(r'^(\d+)\. (.+): R\$ ([\d.,]+)(?: \((.+)\))?$', l)
        if m: prods.append([html.unescape(m.group(2)), m.group(3), m.group(4)])
    assert len(prods) == len(post['produtos']), (post['id'], len(prods))
    for pr, i in zip(prods, post['produtos']):
        pr.append(i); pr[2] = pr[2] or LOJAS[itens[i]['loja']][0]
        pr.append(itens[i]['loja'])
    titulo = limpar(post['tema']); titulo = re.sub(r'\s*\(\d+ produtos?\)$', '', titulo)
    return titulo, data, prods

def rodape(d, loja_txt, data):
    pre = {'Shopee': 'na Shopee', 'Amazon': 'na Amazon', 'Mercado Livre': 'no Mercado Livre', 'Magalu': 'no Magalu', 'AliExpress': 'na AliExpress'}.get(loja_txt, 'nas lojas')
    d.text((W / 2, 1320), 'Preço conferido %s em %s • pode mudar' % (pre, data), font=NUN7(26), fill=ROXO2, anchor='mm')

def capa(post, titulo, data, prods, lojas):
    img, d = novo(); logo(img, d)
    if len(lojas) == 1: etiqueta(d, list(lojas)[0])
    for tam in range(116, 60, -4):
        f = BALOO(tam); ls = quebrar(d, titulo.upper(), f, 920, 4)
        if len(ls) <= 3 and '…' not in ls[-1]: break
    y = 150
    for l in ls: d.text((80, y), l, font=f, fill=ROXO); y += int(tam * 1.12)
    d.text((80, y + 4), 'achadinhos com preço conferido', font=NUN8(38), fill=ROXO2)
    n = len(prods); linhas = [prods[i:i + 3] for i in range(0, n, 3)] if n != 4 else [prods[:2], prods[2:]]
    lado, gap, y0 = 290, 18, y + 80
    if y0 + len(linhas) * (lado + gap) > 1190: lado = max(190, (1190 - y0) // len(linhas) - gap)
    for li, linha in enumerate(linhas):
        tot = len(linha) * lado + (len(linha) - 1) * gap; x = (W - tot) // 2
        for p in linha:
            q = arred(encaixar(foto(p[3]), lado, 14), 30); img.paste(q, (x, y0 + li * (lado + gap)), q); x += lado + gap
    pilula(d, (W - 60 - (larg(d, 'DESLIZE PARA VER', NUN8(40)) + 76), 1205), 'DESLIZE PARA VER', NUN8(40), ROXO, AMARELO)
    rodape(d, LOJAS[list(lojas)[0]][0] if len(lojas) == 1 else 'misto', data); return img

def produto(n, p, data):
    nome, preco, loja_txt, pid, loja = p
    img, d = novo(); logo(img, d); etiqueta(d, loja)
    fr = arred(encaixar(foto(pid), 920, 40), 50); img.paste(fr, (80, 150), fr)
    d.ellipse((60, 130, 160, 230), fill=AMARELO, outline=ROXO, width=6)
    d.text((110, 182), str(n), font=BALOO(60), fill=ROXO, anchor='mm')
    ls = quebrar(d, nome, NUN8(40), 920, 2); y = 1092
    for l in ls: d.text((80, y), l, font=NUN8(40), fill=ROXO); y += 46
    d.text((80, 1190), 'R$ ' + preco, font=BALOO(78), fill=VERM)
    pilula(d, (710, 1190), 'LINK NA BIO', NUN8(40), ROXO, AMARELO)
    rodape(d, LOJAS[loja][0], data); return img

def final(data, lojas):
    img, d = novo(); logo(img, d)
    d.text((W / 2, 520), 'Salve para', font=BALOO(124), fill=ROXO, anchor='mm')
    d.text((W / 2, 650), 'comprar depois', font=BALOO(124), fill=ROXO, anchor='mm')
    f = NUN8(46); w = larg(d, 'LINK NA BIO', f) + 76
    pilula(d, ((W - w) / 2, 780), 'LINK NA BIO', f, ROXO, AMARELO)
    d.text((W / 2, 930), 'Confira o valor na loja antes de comprar.', font=NUN7(34), fill=ROXO2, anchor='mm')
    d.text((W / 2, 1180), 'Publicidade: links de afiliado', font=NUN8(36), fill=ROXO, anchor='mm')
    rodape(d, LOJAS[list(lojas)[0]][0] if len(lojas) == 1 else 'misto', data); return img

def main():
    saida = sys.argv[1]
    posts = {p['id']: p for p in json.load(open(os.path.join(RAIZ, 'dados', 'posts.json'), encoding='utf-8'))}
    itens = {x['id']: x for x in json.load(open(os.path.join(RAIZ, 'dados', 'itens.json'), encoding='utf-8'))}
    for pid in sys.argv[2:]:
        post = posts[pid]; titulo, data, prods = ler(post, itens); lojas = {p[4] for p in prods}
        pasta = os.path.join(saida, pid); os.makedirs(pasta, exist_ok=True)
        cards = [capa(post, titulo, data, prods, lojas)] + [produto(i, p, data) for i, p in enumerate(prods, 1)] + [final(data, lojas)]
        for k, c in enumerate(cards, 1): c.save(os.path.join(pasta, '%02d.jpg' % k), 'JPEG', quality=92)
        print(pid, len(cards), 'cards')
if __name__ == '__main__':
    main()

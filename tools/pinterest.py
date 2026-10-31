#!/usr/bin/env python3 -I
"""Gera os pins do Pinterest (JPEG 1080x1620, 2:3) e a planilha de importação em massa.

Pin NÃO leva preço (pin vive meses; o preço muda). Leva foto, nome, loja e o aviso de publicidade.
A descrição só diz quando o preço foi conferido e manda confirmar na loja. O link do pin é o site.
Usa itens que estão em posts publicados/agendados, têm foto local e conferência dentro de 30 dias.

Uso: FONTES=/tmp/f python3 -I tools/pinterest.py [--por-dia 4] [--inicio AAAA-MM-DD] [--hora 18]
Saída: pinterest/<id>.jpg e pinterest/pins.csv (colunas do envio em massa do Pinterest).
"""
import argparse, csv, datetime, html, importlib.util, json, os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('cards', os.path.join(RAIZ, 'tools', 'cards.py'))
C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
from PIL import Image

SITE = 'https://achadinhosdobinga.com.br/?utm_source=pinterest&utm_medium=pin'
RAW = 'https://raw.githubusercontent.com/herlison14/achadinhos/main/pinterest/'
PH = 1620
QUADRO = {'Casa e cozinha': 'Casa e cozinha', 'Beleza e cuidados': 'Beleza e cuidados', 'Moda, esporte e eletrônicos': 'Moda, esporte e eletrônicos',
          'Mercado e guloseimas': 'Mercado e guloseimas', 'Ferramentas e garagem': 'Ferramentas e garagem',
          'Infantil e brinquedos': 'Infantil e brinquedos', 'Pet': 'Pet'}


def pin(it):
    img = Image.new('RGB', (C.W, PH), C.LAV); d = C.ImageDraw.Draw(img)
    C.logo(img, d); C.etiqueta(d, it['loja'])
    fr = C.arred(C.encaixar(C.foto(it['id']), 920, 40), 50); img.paste(fr, (80, 150), fr)
    nome = html.unescape(it['nome'])
    f = C.NUN8(48); y = 1110
    for l in C.quebrar(d, nome, f, 920, 3):
        d.text((80, y), l, font=f, fill=C.ROXO); y += 56
    texto = 'VER OFERTA NO SITE'; fb = C.NUN8(40)
    C.pilula(d, (80, y + 50), texto, fb, C.ROXO, C.AMARELO)
    d.text((C.W / 2, 1570), 'Publicidade: links de afiliado • confira o preço na loja', font=C.NUN7(28), fill=C.ROXO2, anchor='mm')
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--por-dia', type=int, default=4)
    ap.add_argument('--inicio', default=(datetime.date.today() + datetime.timedelta(days=1)).isoformat())
    ap.add_argument('--hora', type=int, default=18)
    a = ap.parse_args()
    itens = json.load(open(os.path.join(RAIZ, 'dados', 'itens.json'), encoding='utf-8'))
    posts = json.load(open(os.path.join(RAIZ, 'dados', 'posts.json'), encoding='utf-8'))
    usados = []
    for p in posts:
        if p.get('status') in ('publicado', 'agendado'):
            for i in p.get('produtos', []):
                if i not in usados: usados.append(i)
    por_id = {i['id']: i for i in itens}
    hoje = datetime.date.today()
    saida = os.path.join(RAIZ, 'pinterest'); os.makedirs(saida, exist_ok=True)
    lojas = {'shopee': 'Shopee', 'amazon': 'Amazon', 'meli': 'Mercado Livre', 'magalu': 'Magalu', 'aliexpress': 'AliExpress'}
    linhas = []; pulados = 0
    for pid in usados:
        it = por_id.get(pid)
        if not it or (hoje - datetime.date.fromisoformat(it['conferido'])).days > 30: pulados += 1; continue
        if not (os.path.exists(os.path.join(RAIZ, 'img', 'cards', pid + '.jpg')) or os.path.exists(os.path.join(RAIZ, 'img', pid + '.webp'))):
            pulados += 1; continue
        pin(it).save(os.path.join(saida, pid + '.jpg'), 'JPEG', quality=88)
        nome = html.unescape(it['nome']); dt = datetime.date.fromisoformat(it['conferido']).strftime('%d/%m/%Y')
        tag = re.sub(r'[^a-z0-9]', '', C.limpar(lojas[it['loja']]).lower())
        desc = ('%s. Oferta da %s com preço conferido em %s. O preço pode mudar: confirme na loja antes de comprar. '
                'Mais achadinhos no site do Achadinhos do Binga. #achadinhos #ofertas #%s '
                'Publicidade: links de afiliado.') % (nome, lojas[it['loja']], dt, tag)
        linhas.append([nome[:100], RAW + pid + '.jpg', QUADRO.get(it['cat'], 'Achadinhos'), desc[:500], SITE,
                       'achadinhos, ofertas, ' + lojas[it['loja']].lower() + ', ' + it['cat'].lower()])
    ini = datetime.date.fromisoformat(a.inicio)
    with open(os.path.join(saida, 'pins.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Title', 'Media URL', 'Pinterest board', 'Description', 'Link', 'Publish date', 'Keywords'])
        for n, l in enumerate(linhas):
            dia = ini + datetime.timedelta(days=n // a.por_dia)
            hora = a.hora + (n % a.por_dia) * 1
            w.writerow([l[0], l[1], l[2], l[3], l[4], '%sT%02d:00:00' % (dia.isoformat(), min(hora, 23)), l[5]])
    print('pins: %d gerados, %d pulados (sem foto local ou conferência > 30 dias); %s a %s' %
          (len(linhas), pulados, ini.isoformat(), (ini + datetime.timedelta(days=max(0, (len(linhas) - 1) // a.por_dia))).isoformat()))


if __name__ == '__main__':
    main()

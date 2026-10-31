#!/usr/bin/env python3
"""Baixa as fotos listadas em dados/fotos_urls.json (id -> endereço da imagem) para img/cards/<id>.jpg.

Os endereços vêm da página do produto aberta no Chrome do Herlison (og:image / imagem principal).
Roda no GitHub Actions (a nuvem do Claude não alcança os CDNs das lojas). Requer Pillow.
Uso: python3 tools/fotos_urls.py
"""
import io, json, os, sys, urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LISTA = os.path.join(RAIZ, 'dados', 'fotos_urls.json')
PASTA = os.path.join(RAIZ, 'img', 'cards')
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/126.0.0.0 Safari/537.36')

def baixar(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'image/avif,image/webp,image/*,*/*;q=0.8',
                                                'Referer': 'https://www.google.com/'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read(8_000_000)

def main():
    from PIL import Image
    urls = json.load(open(LISTA, encoding='utf-8'))
    os.makedirs(PASTA, exist_ok=True)
    rel = []
    for i, u in urls.items():
        dest = os.path.join(PASTA, i + '.jpg')
        if os.path.exists(dest): continue
        r = {'id': i, 'ok': False}
        try:
            im = Image.open(io.BytesIO(baixar(u))).convert('RGB')
            r['tamanho'] = '%dx%d' % im.size
            if min(im.size) < 250:
                r['erro'] = 'imagem pequena demais'
            else:
                im.thumbnail((1000, 1000), Image.LANCZOS)
                im.save(dest, 'JPEG', quality=90)
                r['ok'] = True
        except Exception as e:
            r['erro'] = str(e)[:90]
        rel.append(r)
        print(r)
    json.dump(rel, open(os.path.join(PASTA, '_relatorio.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('OK: %d de %d' % (sum(1 for r in rel if r['ok']), len(rel)))

if __name__ == '__main__':
    main()

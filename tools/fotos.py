#!/usr/bin/env python3
"""Baixa uma foto melhor (até 600 px) para os itens que só têm miniatura de 80 px.

Lê a página do produto (link de afiliado), procura a imagem principal (og:image e equivalentes),
salva em img/<id>.webp e grava o campo "foto" em dados/itens.json.
Roda no GitHub Actions (o sandbox do Claude não alcança essas lojas). Requer Pillow.
Uso: python3 tools/fotos.py [--todos]   (--todos refaz também os que já têm foto)
"""
import io, json, os, re, sys, html, urllib.request, urllib.error, urllib.parse

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITENS = os.path.join(RAIZ, 'dados', 'itens.json')
PASTA = os.path.join(RAIZ, 'img')
UA = ('Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/126.0.0.0 Mobile Safari/537.36')
HDR = {'User-Agent': UA, 'Accept-Language': 'pt-BR,pt;q=0.9', 'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8'}

def baixar(url, ref=None, limite=4_000_000):
    h = dict(HDR)
    if ref: h['Referer'] = ref
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read(limite), r.geturl(), r.headers.get('Content-Type', '')

META = [
    r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)',
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',
    r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image',
    r'"hiRes"\s*:\s*"([^"]+)"',
    r'data-old-hires=["\']([^"\']+)',
    r'id=["\']landingImage["\'][^>]+src=["\']([^"\']+)',
]

def achar_imagem(corpo, base):
    for pat in META:
        m = re.search(pat, corpo, re.I)
        if m:
            u = html.unescape(m.group(1)).strip()
            if u and not u.startswith('data:'):
                return urllib.parse.urljoin(base, u)
    return None

def main():
    from PIL import Image
    todos = '--todos' in sys.argv
    itens = json.load(open(ITENS, encoding='utf-8'))
    os.makedirs(PASTA, exist_ok=True)
    rel = []
    usadas = {}
    for it in itens:
        if not it['img'].startswith('data:'): continue          # AliExpress/Magalu já têm foto por URL
        dest = os.path.join(PASTA, it['id'] + '.webp')
        if os.path.exists(dest) and it.get('foto') and not todos: continue
        r = {'id': it['id'], 'loja': it['loja'], 'ok': False}
        try:
            corpo, final, ct = baixar(it['href'])
            r['pagina'] = final[:90]
            txt = corpo.decode('utf-8', 'replace')
            u = achar_imagem(txt, final)
            if not u:
                r['erro'] = 'sem imagem na página (%d bytes)' % len(corpo)
            else:
                r['imagem'] = u[:110]
                dados, _, ct2 = baixar(u, ref=final)
                im = Image.open(io.BytesIO(dados)).convert('RGB')
                r['tamanho'] = '%dx%d' % im.size
                usadas[u] = usadas.get(u, 0) + 1
                if usadas[u] > 1 or 'homepagefe' in u or 'shopee-mobilemall' in u:
                    r['erro'] = 'imagem genérica/repetida (não é do produto)'
                elif min(im.size) < 200:
                    r['erro'] = 'imagem pequena demais'
                else:
                    im.thumbnail((600, 600), Image.LANCZOS)
                    im.save(dest, 'WEBP', quality=82, method=6)
                    it['foto'] = 'img/%s.webp' % it['id']
                    r['ok'] = True
        except urllib.error.HTTPError as e:
            r['erro'] = 'HTTP %d' % e.code
        except Exception as e:
            r['erro'] = '%s: %s' % (type(e).__name__, str(e)[:80])
        rel.append(r)
        print(('OK  ' if r['ok'] else 'FALHA'), r['loja'], it['id'], r.get('tamanho', ''), r.get('erro', ''), flush=True)
    with open(ITENS, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(itens, f, ensure_ascii=False, indent=1); f.write('\n')
    with open(os.path.join(PASTA, '_relatorio.json'), 'w', encoding='utf-8') as f:
        json.dump(rel, f, ensure_ascii=False, indent=1)
    por = {}
    for r in rel:
        d = por.setdefault(r['loja'], [0, 0]); d[0 if r['ok'] else 1] += 1
    print('resumo (ok, falha) por loja:', por)

if __name__ == '__main__':
    main()

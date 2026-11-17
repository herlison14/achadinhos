#!/usr/bin/env python3
"""Numeração dos posts para a página "Vi no Insta" (achadinhosdobinga.com.br/ig/).

Cada post ou Story de produto ganha um número fixo (campo "num" em dados/posts.json). O número aparece no card
("LINK NA BIO • Nº 128"), na legenda dos posts de feed e na página /ig/, que lista os produtos de cada post na
ordem em que saíram. Quem toca no link da bio acha o produto pelo número, sem procurar entre centenas de ofertas.

Uso: python3 -I tools/numeros.py   (numera o que faltar e grava; os geradores de card também chamam numerar())
"""
import json, os, re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(RAIZ, 'dados', 'posts.json')
FORMATOS = ('carrossel', 'imagem', 'post', 'story', 'reel')
LINHA = '🔗 Link na bio → produto Nº %d'


def numeravel(p):
    return (p.get('canal', 'ig') == 'ig' and p.get('produtos') and p.get('formato') in FORMATOS
            and p.get('status') not in ('cancelado', 'bloqueado'))


def numerar(posts):
    """Dá número aos posts de produto que ainda não têm, em ordem de data/hora. Devolve quantos numerou.
    Nos posts de feed (não Story) ainda não publicados, acrescenta a linha do número na legenda, antes da
    linha de "Publicidade" (Story não tem legenda visível: o número vai só no card)."""
    prox = max([p.get('num') or 0 for p in posts] + [0]) + 1
    n = 0
    for p in sorted([p for p in posts if numeravel(p) and not p.get('num')], key=lambda p: (p.get('data', ''), p.get('hora') or '', p['id'])):
        p['num'] = prox; prox += 1; n += 1
    for p in posts:
        if p.get('num') and p.get('formato') != 'story' and p.get('status') in ('agendado', 'planejado') and 'Link na bio → produto Nº' not in (p.get('legenda') or ''):
            leg = p.get('legenda') or ''
            linha = LINHA % p['num']
            m = re.search(r'^.*Publicidade.*$', leg, re.M)
            p['legenda'] = (leg[:m.start()] + linha + '\n' + leg[m.start():]) if m else (leg.rstrip() + '\n' + linha)
    return n


def ler_posts():
    return json.load(open(POSTS, encoding='utf-8'))


def gravar_posts(posts):
    """Grava mantendo a indentação que o arquivo já usa (evita diff do arquivo inteiro)."""
    try:
        txt = open(POSTS, encoding='utf-8').read(400)
        m = re.search(r'\n( +)"', txt)
        ind = len(m.group(1)) // 2 if m and txt.lstrip().startswith('[') else 1
        ind = max(1, ind)
    except OSError:
        ind = 1
    with open(POSTS, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(posts, ensure_ascii=False, indent=ind) + '\n')


if __name__ == '__main__':
    ps = ler_posts()
    n = numerar(ps)
    gravar_posts(ps)
    print('%d post(s) numerado(s); último Nº %d' % (n, max([p.get('num') or 0 for p in ps] + [0])))

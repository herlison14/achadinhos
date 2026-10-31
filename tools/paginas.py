"""Páginas estáticas por categoria (ofertas/<slug>/) e por loja (lojas/<loja>/), geradas a partir de dados/itens.json.

Chamado por `vigia.py build`. Só usa dados reais: preço e data de conferência dos itens, e quedas do historico.json.
Nada de preço, desconto ou estoque inventado. Também regrava o sitemap.xml com todas as páginas.
"""
import datetime, html, os, re, unicodedata

SITE = 'https://achadinhosdobinga.com.br/'
LOJAS = {'shopee': 'Shopee', 'amazon': 'Amazon', 'meli': 'Mercado Livre', 'aliexpress': 'AliExpress', 'magalu': 'Magalu'}
EXTRA_CSS = (
    '.pg h1{font-size:clamp(1.7rem,6.4vw,2.4rem);margin:18px 0 8px}.pg .intro{max-width:62ch;color:var(--mut);margin:0 0 14px}'
    '.pg .nav2{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 18px;padding:0;list-style:none}'
    '.pg .nav2 a{display:inline-block;padding:7px 14px;border:1px solid var(--line);border-radius:999px;background:var(--card);'
    'font-weight:800;font-size:.85rem;text-decoration:none}.pg .nav2 a[aria-current]{background:var(--pill);color:var(--pillfg);border-color:var(--pill)}'
    '.pg .crumb{font-size:.85rem;font-weight:800;margin:6px 0 0}.pg .crumb a{color:var(--mut)}'
    '.pg .qd{margin:0 0 16px;padding:12px 14px;border:1px solid var(--line);border-radius:14px;background:var(--card);font-size:.92rem}'
    '.pg .qd b{display:block;margin-bottom:4px}.pg .qd ul{margin:0;padding-left:18px}'
)


def slug(t):
    t = unicodedata.normalize('NFD', t.lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')


def br(n):
    inteiro, dec = ('%.2f' % n).split('.')
    inteiro = '{:,}'.format(int(inteiro)).replace(',', '.')
    return 'R$ %s,%s' % (inteiro, dec)


def _data_br(iso):
    return datetime.date.fromisoformat(iso).strftime('%d/%m/%Y')


def _cabecalho(h):
    """Topo (logo + Instagram) copiado do index.html, com a logo apontando para o arquivo em vez de data URI."""
    m = re.search(r'<div class="wrap brand">.*?</div>', h, re.S)
    t = m.group(0)
    t = re.sub(r'(<a class="lg" href=")[^"]*(")', r'\1/\2', t)
    t = re.sub(r'src="data:[^"]+"', 'src="/img/marca.webp"', t, count=1)
    t = t.replace('href="privacidade.html"', 'href="/privacidade.html"')
    return t


def _pagina(h, estilo, cab, titulo, desc, caminho, h1, intro, corpo, navs, ld, aviso):
    url = SITE + caminho
    t = html.escape(titulo)
    return (
        '<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        '<title>%s</title>\n<meta name="description" content="%s">\n<link rel="canonical" href="%s">\n'
        '<meta property="og:type" content="website"><meta property="og:locale" content="pt_BR">'
        '<meta property="og:site_name" content="Achadinhos do Binga"><meta property="og:title" content="%s">'
        '<meta property="og:description" content="%s"><meta property="og:url" content="%s">\n'
        '<link rel="icon" type="image/png" sizes="32x32" href="/img/favicon-32.png">\n'
        '<link rel="apple-touch-icon" href="/img/apple-touch-icon.png">\n'
        '<link rel="stylesheet" href="/fontes.css">\n<style>%s%s</style>\n%s\n</head>\n'
        '<body class="pg" id="topo">\n%s\n<div class="wrap">\n<p class="crumb"><a href="/">&larr; Todas as ofertas</a></p>\n'
        '<h1>%s</h1>\n<p class="intro">%s</p>\n%s\n<main id="ofertas">\n%s</main>\n'
        '<footer>\n<p class="aviso">%s</p>\n'
        '<p class="fl"><a href="https://instagram.com/achadinhosdobinga" rel="noopener">Instagram @achadinhosdobinga</a>'
        '<a href="https://t.me/achadinhosdobinga" rel="noopener">Telegram</a>'
        '<a href="https://whatsapp.com/channel/0029VbDhqE4FSAt3fXMI7f1S" rel="noopener">WhatsApp</a>'
        '<a href="/privacidade.html">Privacidade</a><span>&copy; 2026 Achadinhos do Binga</span></p>\n</footer>\n</div>\n'
        '<script src="/cliques.js" defer></script>\n</body>\n</html>\n'
        % (t, html.escape(desc), url, t, html.escape(desc), url, estilo, EXTRA_CSS, ld, cab, h1, intro, navs, corpo, aviso)
    )


def gerar(raiz, vis, quedas_lista, datas_texto, render, num, dados_estruturados, hoje):
    h = open(os.path.join(raiz, 'index.html'), encoding='utf-8').read()
    estilo = re.search(r'<style[^>]*>(.*?)</style>', h, re.S).group(1)
    cab = _cabecalho(h)
    base, resto = datas_texto(vis)
    aviso = ('Publicidade: estes são links de afiliado da Shopee, Amazon, Mercado Livre, AliExpress e Magalu e eu posso receber '
             'comissão pelas compras feitas por eles, sem custo extra para você. Preços e estoque são os conferidos em %s%s e podem '
             'ter mudado. Confirme o valor na loja antes de comprar. No Magalu, o preço mostrado é o do Pix; no cartão pode ser maior. '
             'Como Associado da Amazon, eu ganho com compras qualificadas.' % (base, resto))
    cats = sorted({i['cat'] for i in vis})
    lojas = [l for l in LOJAS if any(i['loja'] == l for i in vis)]
    q_por_id = {q['id']: q for q in quedas_lista}

    def nav(atual):
        a = ['<ul class="nav2" aria-label="Categorias e lojas">']
        for c in cats:
            cur = ' aria-current="page"' if atual == ('c', c) else ''
            a.append('<li><a href="/ofertas/%s/"%s>%s</a></li>' % (slug(c), cur, html.escape(c)))
        for l in lojas:
            cur = ' aria-current="page"' if atual == ('l', l) else ''
            a.append('<li><a href="/lojas/%s/"%s>%s</a></li>' % (l, cur, LOJAS[l]))
        a.append('</ul>')
        return ''.join(a)

    def bloco_quedas(itens):
        qs = [q_por_id[i['id']] for i in itens if i['id'] in q_por_id]
        if not qs:
            return ''
        qs.sort(key=lambda q: -q['pct'])
        por_id = {i['id']: i for i in itens}
        li = ''.join('<li>%s: de R$ %s para R$ %s (conferido em %s)</li>' % (por_id[q['id']]['nome'], q['antes'], q['agora'], _data_br(q['data']))
                     for q in qs[:5])
        return '<div class="qd"><b>Caiu de preço nas últimas conferências</b><ul>%s</ul></div>' % li

    def faixa(itens):
        v = [num(i['preco']) for i in itens]
        return br(min(v)), br(max(v))

    paginas = []  # (caminho, html)
    for c in cats:
        its = sorted([i for i in vis if i['cat'] == c], key=lambda i: num(i['preco']))
        mn, mx = faixa(its)
        ls = sorted({LOJAS[i['loja']] for i in its})
        intro = ('%d ofertas de %s com preço conferido, de %s a %s, em %s. A lista está ordenada do menor para o maior preço conferido; '
                 'o valor pode ter mudado, então confirme na loja.' % (len(its), c.lower(), mn, mx, ', '.join(ls)))
        corpo = '<ul>' + ''.join(render(i) for i in its) + '</ul>'
        caminho = 'ofertas/%s/' % slug(c)
        paginas.append((caminho, _pagina(
            h, estilo, cab, '%s: ofertas com preço conferido | Achadinhos do Binga' % c,
            'Veja %d ofertas de %s com preço conferido na Shopee, Amazon, Mercado Livre, AliExpress e Magalu. De %s a %s.' % (len(its), c.lower(), mn, mx),
            caminho, 'Ofertas de %s' % html.escape(c), intro, corpo, nav(('c', c)),
            dados_estruturados(its), aviso).replace('<main id="ofertas">', bloco_quedas(its) + '<main id="ofertas">', 1)))
    for l in lojas:
        its = [i for i in vis if i['loja'] == l]
        mn, mx = faixa(its)
        partes = []
        for c in sorted({i['cat'] for i in its}):
            sub = sorted([i for i in its if i['cat'] == c], key=lambda i: num(i['preco']))
            partes.append('<h2>%s</h2>\n<ul>%s</ul>\n' % (html.escape(c), ''.join(render(i) for i in sub)))
        intro = ('%d ofertas da %s com preço conferido, de %s a %s, divididas por categoria. O valor pode ter mudado, '
                 'então confirme na loja antes de comprar.' % (len(its), LOJAS[l], mn, mx))
        caminho = 'lojas/%s/' % l
        paginas.append((caminho, _pagina(
            h, estilo, cab, 'Ofertas da %s com preço conferido | Achadinhos do Binga' % LOJAS[l],
            'Veja %d ofertas da %s com preço conferido, de %s a %s, por categoria.' % (len(its), LOJAS[l], mn, mx),
            caminho, 'Ofertas da %s' % LOJAS[l], intro, ''.join(partes), nav(('l', l)),
            dados_estruturados(its), aviso).replace('<main id="ofertas">', bloco_quedas(its) + '<main id="ofertas">', 1)))

    for caminho, conteudo in paginas:
        pasta = os.path.join(raiz, caminho)
        os.makedirs(pasta, exist_ok=True)
        with open(os.path.join(pasta, 'index.html'), 'w', encoding='utf-8', newline='\n') as f:
            f.write(conteudo)

    # Links da página inicial para as novas páginas (é por eles que o Google descobre e entende o site)
    topo = ''.join('<li><a href="/ofertas/%s/">%s</a></li>' % (slug(c), html.escape(c)) for c in cats)
    topo += ''.join('<li><a href="/lojas/%s/">%s</a></li>' % (l, LOJAS[l]) for l in lojas)
    bloco = '<nav class="pgs" aria-label="Ofertas por categoria e por loja"><h2>Ver por categoria e por loja</h2><ul class="nav2">%s</ul></nav>' % topo
    h2, n = re.subn(r'(<!--paginas-inicio-->).*?(<!--paginas-fim-->)', lambda m: m.group(1) + bloco + m.group(2), h, flags=re.S)
    assert n == 1, 'faltam os marcadores <!--paginas-inicio--><!--paginas-fim--> no index.html'
    with open(os.path.join(raiz, 'index.html'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(h2)

    urls = [('', '1.0', 'weekly'), ('privacidade.html', '0.3', 'yearly')] + [(c, '0.8', 'weekly') for c, _ in paginas]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, p, f in urls:
        sm.append('<url><loc>%s%s</loc><lastmod>%s</lastmod><changefreq>%s</changefreq><priority>%s</priority></url>' % (SITE, u, hoje.isoformat(), f, p))
    sm.append('</urlset>')
    with open(os.path.join(raiz, 'sitemap.xml'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(sm) + '\n')
    return len(paginas)

#!/usr/bin/env python3
"""Vigia de preços do Achadinhos do Binga.

Fonte de verdade: dados/itens.json (ofertas) e dados/historico.json (preços por dia).
O index.html é gerado a partir deles. Sem dependências externas (Python 3.8+).

Comandos:
  init                        extrai itens.json do index.html atual (uso único)
  build                       regera o index.html a partir de dados/itens.json
  atualizar ARQUIVO.csv       aplica novos preços (colunas: id_ou_link;preco;data) e registra histórico
  relatorio [--dias N]        mostra quedas/altas, itens sem conferência recente e totais
  importar [--data AAAA-MM-DD]  sincroniza dados/ com o index.html (use se a página foi editada à mão)
  novo --loja L --cat "Categoria" --nome "Nome" --href URL --img URL --preco 12,34 [--ex ".."] [--pre ".."] [--pos ".."] [--data AAAA-MM-DD]
  remover ID                  tira uma oferta de dados/itens.json (o histórico fica guardado)
Datas nos arquivos de dados: AAAA-MM-DD. Na tela e nos relatórios: DD/MM/AAAA.
"""
import sys, re, json, hashlib, csv, datetime, os, html

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDX = os.path.join(RAIZ, 'index.html')
ITENS = os.path.join(RAIZ, 'dados', 'itens.json')
HIST = os.path.join(RAIZ, 'dados', 'historico.json')
NOMES = {'shopee': 'Shopee', 'amazon': 'Amazon', 'meli': 'Mercado Livre', 'aliexpress': 'AliExpress', 'magalu': 'Magalu'}
OMITIR_APOS_DIAS = 30   # item sem conferência há mais de N dias sai da página (build)
ALERTA_APOS_DIAS = 7    # relatório avisa itens sem conferência há mais de N dias

def loja_de(href):
    if 'shopee' in href: return 'shopee'
    if 'amazon' in href: return 'amazon'
    if 'meli.la' in href or 'mercadolivre' in href: return 'meli'
    if 'aliexpress' in href: return 'aliexpress'
    if 'magazinevoce' in href: return 'magalu'
    return '?'

def id_de(href): return hashlib.sha1(href.encode()).hexdigest()[:8]
def br(d): return datetime.date.fromisoformat(d).strftime('%d/%m/%Y')
def num(p): return float(p.replace('.', '').replace(',', '.'))
def fmt(v):
    s = '{:,.2f}'.format(v)
    return s.replace(',', 'X').replace('.', ',').replace('X', '.')

def ler(p, padrao):
    if not os.path.exists(p): return padrao
    with open(p, encoding='utf-8') as f: return json.load(f)
def gravar(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1); f.write('\n')

LI = re.compile(r'<li class="it">.*?</li>', re.S)
SEC = re.compile(r'(<h2>([^<]+)</h2>\s*<ul>)(.*?)(</ul>)', re.S)

def render(it):
    pre = it.get('pre', '')   # HTML cru antes do preço (ex.: <small>a partir de </small>)
    pos = it.get('pos', '')   # HTML cru depois do preço (ex.:  <small>no Pix</small>)
    ex = '<span class="ex">%s</span>' % it['ex'] if it.get('ex') is not None else ''
    return ('<li class="it"><a href="%s" rel="noopener sponsored"><img class="ph" alt="" width="64" height="64" loading="lazy" src="%s">'
            '<span class="tx"><span class="nm">%s</span>%s<span class="pr">%s<b>R$ %s</b>%s</span></span><span class="go">%s</span></a></li>'
            % (it['href'], it['img'], it['nome'], ex, pre, it['preco'], pos, it['cta']))

def parse(li, cat, datas):
    href = re.search(r'href="([^"]+)"', li).group(1)
    pr = re.search(r'<span class="pr">(.*?)</span></span><span class="go">', li, re.S).group(1)
    m_b = re.search(r'<b>R\$ ([\d.]+,\d\d)</b>', pr)
    antes, depois = pr.split(m_b.group(0))
    ex = re.search(r'<span class="ex">(.*?)</span>', li, re.S)
    l = loja_de(href)
    it = dict(id=id_de(href), loja=l, cat=cat, nome=re.search(r'<span class="nm">(.*?)</span>', li, re.S).group(1),
              href=href, img=re.search(r' src="([^"]+)"', li).group(1), preco=m_b.group(1),
              cta=re.search(r'<span class="go">(.*?)</span>', li, re.S).group(1), conferido=datas.get(l, datas['*']))
    if antes: it['pre'] = antes
    if depois: it['pos'] = depois
    if ex: it['ex'] = ex.group(1)
    return it

def cmd_init(datas):
    h = open(IDX, encoding='utf-8').read()
    itens = []
    for m in SEC.finditer(h):
        for li in LI.findall(m.group(3)):
            itens.append(parse(li, m.group(2), datas))
    ids = [i['id'] for i in itens]
    assert len(ids) == len(set(ids)), 'links duplicados'
    gravar(ITENS, itens)
    hist = ler(HIST, {})
    for i in itens:
        hist.setdefault(i['id'], [[i['conferido'], i['preco']]])
    gravar(HIST, hist)
    print('itens:', len(itens))

def datas_texto(itens):
    """'22/10/2026 (AliExpress e Magalu: 26/10/2026)' a partir das datas dos itens."""
    por_loja = {}
    for i in itens:
        por_loja[i['loja']] = min(por_loja.get(i['loja'], '9999'), i['conferido'])
    base = min(por_loja.values())
    resto = {}
    for l, d in por_loja.items():
        if d != base: resto.setdefault(d, []).append(NOMES[l])
    partes = []
    for d in sorted(resto):
        nomes = sorted(resto[d]); n = nomes[0] if len(nomes) == 1 else ', '.join(nomes[:-1]) + ' e ' + nomes[-1]
        partes.append('%s: %s' % (n, br(d)))
    return br(base), (' (%s)' % '; '.join(partes) if partes else '')

def cmd_build():
    itens = ler(ITENS, [])
    hoje = datetime.date.today()
    vis = []
    omitidos = []
    for i in itens:
        idade = (hoje - datetime.date.fromisoformat(i['conferido'])).days
        if idade > OMITIR_APOS_DIAS: omitidos.append((i, idade))
        else: vis.append(i)
    h = open(IDX, encoding='utf-8').read()
    cats = {m.group(2) for m in SEC.finditer(h)}
    for i in vis:
        assert i['cat'] in cats, 'categoria sem seção no template: ' + i['cat']
    def troca(m):
        corpo = ''.join(render(i) for i in vis if i['cat'] == m.group(2))
        return m.group(1) + corpo + m.group(4)
    h = SEC.sub(troca, h)
    base, resto = datas_texto(vis)
    h, n1 = re.subn(r'(Preços conferidos em <b>)[^<]+(</b>)[^<]*(</span>)', lambda m: m.group(1) + base + m.group(2) + resto + m.group(3), h)
    h, n2 = re.subn(r'(<b id="n-of">)\d+(</b>.*?com preço conferido em )[^<]*?(\.</p>)',
                    lambda m: m.group(1) + str(len(vis)) + m.group(2) + base + resto + m.group(3), h, flags=re.S)
    assert n1 == 1 and n2 == 1, (n1, n2)
    open(IDX, 'w', encoding='utf-8', newline='\n').write(h)
    print('build: %d itens na página' % len(vis))
    for i, d in omitidos: print('  OMITIDO (sem conferência há %d dias): %s' % (d, i['nome']))

def cmd_atualizar(arq):
    itens = ler(ITENS, []); hist = ler(HIST, {})
    idx = {i['id']: i for i in itens}
    por_link = {i['href']: i for i in itens}
    mudou = 0; igual = 0; erros = []
    with open(arq, encoding='utf-8') as f:
        for lin in csv.reader(f, delimiter=';'):
            if not lin or lin[0].startswith('#') or lin[0] == 'id': continue
            chave, preco, data = [c.strip() for c in lin[:3]]
            it = idx.get(chave) or por_link.get(chave)
            if not it: erros.append('não achei: ' + chave); continue
            if '/' in data: data = datetime.datetime.strptime(data, '%d/%m/%Y').date().isoformat()
            datetime.date.fromisoformat(data)
            preco = fmt(num(preco)) if re.fullmatch(r'[\d.]+,\d\d', preco) is None else preco
            ant = it['preco']
            h = hist.setdefault(it['id'], [])
            if not h or h[-1][1] != preco or h[-1][0] != data: h.append([data, preco])
            if preco != ant:
                mudou += 1
                print('%s  %s: R$ %s -> R$ %s (%+.1f%%)' % ('QUEDA' if num(preco) < num(ant) else 'ALTA ', it['nome'][:50], ant, preco, (num(preco) / num(ant) - 1) * 100))
                it['preco'] = preco
            else: igual += 1
            it['conferido'] = data
    gravar(ITENS, itens); gravar(HIST, hist)
    print('atualizados: %d mudaram, %d iguais, %d erros' % (mudou, igual, len(erros)))
    for e in erros: print('  ', e)

def cmd_relatorio(dias):
    itens = ler(ITENS, []); hist = ler(HIST, {}); hoje = datetime.date.today()
    print('Itens:', len(itens), '| por loja:', {NOMES[l]: sum(1 for i in itens if i['loja'] == l) for l in NOMES})
    quedas = []
    for i in itens:
        h = hist.get(i['id'], [])
        if len(h) >= 2 and h[-1][1] != h[-2][1]:
            quedas.append((num(h[-1][1]) / num(h[-2][1]) - 1, i, h[-2], h[-1]))
    print('\nVariações recentes (última mudança de preço):')
    for v, i, a, b in sorted(quedas)[:20]:
        print('  %+.1f%%  %s: R$ %s (%s) -> R$ %s (%s) [%s]' % (v * 100, i['nome'][:45], a[1], br(a[0]), b[1], br(b[0]), NOMES[i['loja']]))
    if not quedas: print('  nenhuma ainda (histórico começa em', br(min(p[0] for h in hist.values() for p in h)) + ')')
    velhos = [(hoje - datetime.date.fromisoformat(i['conferido'])).days for i in itens]
    print('\nSem conferência há mais de %d dias:' % dias)
    n = 0
    for i, d in sorted(zip(itens, velhos), key=lambda x: -x[1]):
        if d > dias:
            n += 1; print('  %3d dias  [%s] %s  (%s)  id=%s' % (d, NOMES[i['loja']], i['nome'][:50], br(i['conferido']), i['id']))
    if not n: print('  nenhum')

CTA = {'shopee': 'Ver na Shopee', 'amazon': 'Ver na Amazon', 'meli': 'Ver no Mercado Livre', 'aliexpress': 'Ver no AliExpress', 'magalu': 'Ver no Magalu'}

def cmd_importar(data):
    """Lê o index.html e alinha dados/ com ele: preço novo -> atualiza + histórico; item novo -> entra; item sumido -> sai."""
    h = open(IDX, encoding='utf-8').read()
    itens = ler(ITENS, []); hist = ler(HIST, {})
    antigos = {i['id']: i for i in itens}
    novos = []
    for m in SEC.finditer(h):
        for li in LI.findall(m.group(3)):
            n = parse(li, m.group(2), {'*': data, 'shopee': data, 'amazon': data, 'meli': data, 'aliexpress': data, 'magalu': data})
            a = antigos.get(n['id'])
            if a:
                if a['preco'] != n['preco']:
                    print('PREÇO  %s: R$ %s -> R$ %s' % (n['nome'][:50], a['preco'], n['preco']))
                    hist.setdefault(n['id'], []).append([data, n['preco']])
                    a['preco'] = n['preco']; a['conferido'] = data
                a.update({k: n[k] for k in ('cat', 'nome', 'img', 'cta')})
                for k in ('pre', 'pos', 'ex'):
                    if k in n: a[k] = n[k]
                    else: a.pop(k, None)
                novos.append(a)
            else:
                print('NOVO   %s (R$ %s)' % (n['nome'][:50], n['preco']))
                hist[n['id']] = [[data, n['preco']]]
                novos.append(n)
    sumiram = [i for i in itens if i['id'] not in {n['id'] for n in novos}]
    for i in sumiram: print('SAIU   %s' % i['nome'][:50])
    gravar(ITENS, novos); gravar(HIST, hist)
    print('importar: %d itens (%d novos, %d removidos)' % (len(novos), len([n for n in novos if n['id'] not in antigos]), len(sumiram)))

def cmd_novo(a):
    g = lambda k, d=None: a[a.index('--' + k) + 1] if '--' + k in a else d
    for k in ('loja', 'cat', 'nome', 'href', 'img', 'preco'):
        if g(k) is None: sys.exit('faltou --' + k)
    loja = g('loja'); data = g('data', datetime.date.today().isoformat())
    assert loja in NOMES, 'loja deve ser uma de: ' + ', '.join(NOMES)
    assert loja_de(g('href')) == loja, 'o link não parece ser da loja informada'
    assert re.fullmatch(r'[\d.]+,\d\d', g('preco')), 'preço no formato 1.234,56'
    itens = ler(ITENS, []); hist = ler(HIST, {})
    it = dict(id=id_de(g('href')), loja=loja, cat=g('cat'), nome=html.escape(g('nome'), quote=False), href=g('href'), img=g('img'),
              preco=g('preco'), cta=CTA[loja], conferido=data)
    for k in ('ex', 'pre', 'pos'):
        if g(k): it[k] = g(k)
    assert it['id'] not in {i['id'] for i in itens}, 'esse link já está na lista'
    itens.append(it); hist[it['id']] = [[data, it['preco']]]
    gravar(ITENS, itens); gravar(HIST, hist)
    print('novo: id=%s' % it['id'])

def cmd_remover(i):
    itens = ler(ITENS, [])
    alvo = [x for x in itens if x['id'] == i]
    if not alvo: sys.exit('id não encontrado')
    gravar(ITENS, [x for x in itens if x['id'] != i]); print('removido:', alvo[0]['nome'])

if __name__ == '__main__':
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(1)
    if a[0] == 'init':
        cmd_init({'aliexpress': '2026-10-26', 'magalu': '2026-10-26', '*': '2026-10-22'})
    elif a[0] == 'build': cmd_build()
    elif a[0] == 'atualizar': cmd_atualizar(a[1])
    elif a[0] == 'importar': cmd_importar(a[a.index('--data') + 1] if '--data' in a else datetime.date.today().isoformat())
    elif a[0] == 'novo': cmd_novo(a)
    elif a[0] == 'remover': cmd_remover(a[1])
    elif a[0] == 'relatorio': cmd_relatorio(int(a[a.index('--dias') + 1]) if '--dias' in a else ALERTA_APOS_DIAS)
    else: print(__doc__); sys.exit(1)

#!/usr/bin/env python3
"""Conferidor de preços do Achadinhos do Binga, para rodar no celular (Termux).

Usa o IP da sua casa (as lojas bloqueiam servidores) para ler o preço atual de cada
oferta e alimentar o vigia (tools/vigia.py). Só biblioteca padrão do Python 3.

  python3 -I tools/conferidor_celular.py               # TESTE: mostra o que encontrou, não grava nada
  python3 -I tools/conferidor_celular.py --aplicar     # grava, regenera o site, confere e publica (git push)

Regras (as mesmas da rotina atual):
  * só entra no CSV preço realmente lido; na dúvida o item fica sem conferir (nunca inventa preço);
  * variação maior que 25% em relação ao preço registrado NÃO é gravada (provável erro de leitura): vai para o relatório;
  * Shopee e AliExpress ficam de fora (exigem navegador logado): continuam na rotina do computador; adidas também
    (os termos da Awin proíbem extração automatizada);
  * não clica no link de afiliado a cada conferência: Amazon e Awin são lidos pela página da loja; link curto
    (meli.la) é aberto uma única vez por item e o destino fica no cache local;
  * só publica se `sincronia.py` terminar sem ERRO; se falhar, desfaz a alteração local e mantém o CSV.
"""
import argparse, csv, datetime, gzip, html, json, os, random, re, subprocess, sys, time, zlib
import urllib.error, urllib.parse, urllib.request

UA = ('Mozilla/5.0 (Linux; Android 13; SM-G780G) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0.0.0 Mobile Safari/537.36')
FORA = {'shopee', 'aliexpress', 'adidas'}  # navegador logado / ambíguos / termos da adidas proíbem leitura automática
LIMITE_VARIACAO = 0.25                     # acima disso: não grava, só avisa
HOME = os.path.expanduser('~')
CACHE = os.path.join(HOME, '.achadinhos_cache_urls.json')
SAIDA = os.path.join(HOME, 'achadinhos-saida')


# ---------- util ----------
def num(p): return float(p.replace('.', '').replace(',', '.'))
def fmt(v): return '{:,.2f}'.format(v).replace(',', 'X').replace('.', ',').replace('X', '.')
def br(d): return d.strftime('%d/%m/%Y')


def para_float(x):
    if isinstance(x, (int, float)): return float(x)
    s = re.sub(r'[^\d.,]', '', str(x))
    if not s: return None
    if ',' in s: s = s.replace('.', '').replace(',', '.')
    try: return float(s)
    except ValueError: return None


class Bloqueio(Exception): pass


def buscar(url, timeout=20):
    """GET com cabeçalhos de celular. Devolve (url_final, texto)."""
    req = urllib.request.Request(url, headers={
        'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml', 'Accept-Language': 'pt-BR,pt;q=0.9',
        'Accept-Encoding': 'gzip, deflate'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(3_000_000); enc = (r.headers.get('Content-Encoding') or '').lower(); final = r.geturl()
    except urllib.error.HTTPError as e:
        if e.code in (403, 429, 503): raise Bloqueio('HTTP %d' % e.code)
        raise
    if enc == 'gzip': raw = gzip.decompress(raw)
    elif enc == 'deflate': raw = zlib.decompress(raw)
    return final, raw.decode('utf-8', 'replace')


# ---------- extração de preço ----------
def _ofertas(d, saida):
    if isinstance(d, list):
        for x in d: _ofertas(x, saida)
    elif isinstance(d, dict):
        tipo = d.get('@type'); tipos = tipo if isinstance(tipo, list) else [tipo]
        if any(t in ('Offer', 'AggregateOffer') for t in tipos) or 'price' in d or 'lowPrice' in d:
            p = d.get('price', d.get('lowPrice'))
            if p is None and isinstance(d.get('priceSpecification'), dict): p = d['priceSpecification'].get('price')
            if p is not None: saida.append((para_float(p), str(d.get('availability', ''))))
        for k in ('offers', 'hasVariant', '@graph', 'mainEntity', 'item'):
            if k in d: _ofertas(d[k], saida)


def preco_jsonld(t):
    ofs = []
    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', t, re.S | re.I):
        try: _ofertas(json.loads(m.group(1).strip()), ofs)
        except ValueError: continue
    ofs = [(p, a) for p, a in ofs if p]
    if not ofs: return None, 'sem_dado'
    if all('OutOfStock' in a or 'SoldOut' in a for _, a in ofs): return None, 'sem_estoque'
    precos = {p for p, a in ofs if not ('OutOfStock' in a or 'SoldOut' in a)}
    return (precos.pop(), 'ok') if len(precos) == 1 else (None, 'ambiguo')


def preco_meta(t):
    for pad in (r'itemprop=["\']price["\'][^>]*content=["\']([^"\']+)',
                r'content=["\']([^"\']+)["\'][^>]*itemprop=["\']price["\']',
                r'property=["\'](?:product|og):price:amount["\'][^>]*content=["\']([^"\']+)',
                r'content=["\']([^"\']+)["\'][^>]*property=["\'](?:product|og):price:amount["\']'):
        m = re.search(pad, t, re.I)
        if m and para_float(m.group(1)): return para_float(m.group(1)), 'ok'
    return None, 'sem_dado'


def preco_amazon(t):
    low = t.lower()
    if 'captcha' in low or 'api-services-support@amazon.com' in low or 'digite os caracteres' in low:
        raise Bloqueio('captcha')
    if 'id="outofstock"' in low or 'não disponível no momento' in low or 'indisponível' in low[:200000] and 'a-offscreen' not in low:
        return None, 'sem_estoque'
    m = re.search(r'priceToPay[^>]*>.*?a-offscreen[^>]*>\s*R\$(?:&nbsp;|\s|\xa0)*([\d.]+,\d{2})', t, re.S)
    return (num(m.group(1)), 'ok') if m else (None, 'sem_dado')


def preco_magalu(t):
    m = re.search(r'R\$(?:&nbsp;|\s|\xa0)*([\d.]+,\d{2})(?:\s|<[^>]*>)*(?:no|à vista no)\s*Pix', t, re.I)
    return (num(m.group(1)), 'ok') if m else (None, 'sem_dado')


def extrair(loja, t):
    if loja == 'amazon':
        r = preco_amazon(t)
    elif loja == 'magalu':
        r = preco_magalu(t)
        if r[0] is None: r = preco_jsonld(t)
    else:
        r = preco_jsonld(t)
        if r[0] is None and r[1] == 'sem_dado': r = preco_meta(t)
    return r


# ---------- onde ler ----------
def limpa(u):
    p = urllib.parse.urlparse(u)
    return urllib.parse.urlunparse((p.scheme, p.netloc, p.path, '', '', ''))


def alvo(it, cache):
    """URL da página do produto, sem clicar no link de afiliado quando dá para evitar."""
    if it['id'] in cache: return cache[it['id']]
    h, loja = it['href'], it['loja']; p = urllib.parse.urlparse(h)
    if 'awin1.com' in p.netloc:
        ued = urllib.parse.parse_qs(p.query).get('ued', [None])[0]
        url = ued
    elif loja == 'amazon':
        m = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', h)
        url = ('https://www.amazon.com.br/dp/' + m.group(1)) if m else None
        if not url:
            final, _ = buscar(h); m = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', final)
            url = ('https://www.amazon.com.br/dp/' + m.group(1)) if m else None
    elif loja == 'magalu':
        url = h
    elif loja == 'meli':
        final, _ = buscar(h); url = limpa(final)        # abre o link curto UMA vez; depois usa o cache
    else:
        url = None
    if url: cache[it['id']] = url
    return url


# ---------- seleção ----------
def escolher(itens, posts, limite, lojas, hoje):
    ids_post = set()
    for p in posts:
        if p.get('status') in ('agendado', 'planejado') and p.get('produtos'):
            try: d = datetime.date.fromisoformat(p['data'])
            except (KeyError, ValueError): continue
            if 0 <= (d - hoje).days <= 3: ids_post.update(p['produtos'])
    cand = [i for i in itens if i['loja'] not in FORA and (not lojas or i['loja'] in lojas)]
    cand.sort(key=lambda i: (i['id'] not in ids_post, i['conferido']))
    return cand[:limite]


# ---------- execução ----------
def sh(args, cwd, **kw):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, **kw)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Conferidor de preços (celular)')
    ap.add_argument('--repo', default=None, help='pasta do repositório (padrão: a do script ou a atual)')
    ap.add_argument('--limite', type=int, default=40, help='itens por rodada (padrão 40)')
    ap.add_argument('--lojas', default='', help='só estas lojas, ex.: amazon,magalu')
    ap.add_argument('--aplicar', action='store_true', help='grava, regenera, confere e publica')
    ap.add_argument('--sem-git', action='store_true', help='com --aplicar: não faz pull/commit/push')
    a = ap.parse_args(argv)
    aqui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo = a.repo or (aqui if os.path.exists(os.path.join(aqui, 'dados', 'itens.json')) else os.getcwd())
    if not os.path.exists(os.path.join(repo, 'dados', 'itens.json')): sys.exit('Não achei dados/itens.json em ' + repo)

    if a.aplicar and not a.sem_git:
        r = sh(['git', 'pull', '--rebase', '--autostash'], repo)
        if r.returncode: sys.exit('git pull falhou:\n' + r.stderr)
    ler = lambda f, pad: json.load(open(os.path.join(repo, f), encoding='utf-8')) if os.path.exists(os.path.join(repo, f)) else pad
    itens, posts = ler('dados/itens.json', []), ler('dados/posts.json', [])
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    hoje = datetime.date.today()
    lojas = {x.strip() for x in a.lojas.split(',') if x.strip()}
    lista = escolher(itens, posts, a.limite, lojas, hoje)
    print('Conferindo %d itens (%s)\n' % (len(lista), 'APLICAR' if a.aplicar else 'TESTE: nada será gravado'))

    achados, pend, resumo, bloqueios, ultimo = [], [], {}, {}, {}
    for it in lista:
        loja = it['loja']; r = resumo.setdefault(loja, {})
        def anota(k): r[k] = r.get(k, 0) + 1
        if bloqueios.get(loja, 0) >= 3: anota('pulado'); continue
        espera = ultimo.get(loja, 0) + random.uniform(2.5, 5.5) - time.time()
        if espera > 0: time.sleep(espera)
        try:
            url = alvo(it, cache)
            if not url: anota('sem_url'); continue
            _, t = buscar(url); ultimo[loja] = time.time()
            preco, estado = extrair(loja, t)
            if loja == 'dafiti' and estado == 'sem_estoque': estado = 'sem_dado'   # leitura por robô marca tudo esgotado (CLAUDE.md)
        except Bloqueio as e:
            bloqueios[loja] = bloqueios.get(loja, 0) + 1; ultimo[loja] = time.time()
            anota('bloqueado'); print('  [%s] BLOQUEIO (%s): %s' % (loja, e, it['nome'][:40])); continue
        except Exception as e:
            anota('erro'); print('  [%s] erro (%s): %s' % (loja, type(e).__name__, it['nome'][:40])); continue
        reg = num(it['preco'])
        if preco is None:
            anota(estado)
            if estado == 'sem_estoque': pend.append('SEM ESTOQUE: [%s] %s (id %s)' % (loja, it['nome'][:45], it['id']))
            print('  [%s] %-9s %s' % (loja, estado, it['nome'][:50])); continue
        var = preco / reg - 1
        if abs(var) > LIMITE_VARIACAO:
            anota('suspeito'); pend.append('CONFERIR À MÃO: [%s] %s: registrado R$ %s, lido R$ %s (%+.0f%%)' % (loja, it['nome'][:40], it['preco'], fmt(preco), var * 100))
            print('  [%s] SUSPEITO  %s: %s -> %s' % (loja, it['nome'][:40], it['preco'], fmt(preco))); continue
        anota('igual' if fmt(preco) == it['preco'] else 'mudou')
        achados.append((it, fmt(preco)))
        if fmt(preco) != it['preco']: print('  [%s] %+.1f%%  %s: %s -> %s' % (loja, var * 100, it['nome'][:40], it['preco'], fmt(preco)))

    json.dump(cache, open(CACHE, 'w'))
    print('\nResumo por loja (igual = coincide com o registrado; mudou = preço novo; o resto não entra):')
    for loja, r in sorted(resumo.items()): print('  %-10s %s' % (loja, ', '.join('%s %d' % (k, v) for k, v in sorted(r.items()))))
    for p in pend: print('  !', p)
    print('\nConfirmados: %d de %d. Shopee e AliExpress continuam na rotina do computador.' % (len(achados), len(lista)))
    if not achados: return 0

    os.makedirs(SAIDA, exist_ok=True)
    arq = os.path.join(SAIDA, 'precos_%s.csv' % hoje.isoformat())
    with open(arq, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(['id', 'preco', 'data'])
        for it, pr in achados: w.writerow([it['id'], pr, br(hoje)])
    print('CSV:', arq)
    if not a.aplicar:
        print('\nTeste concluído. Se a tabela acima parece certa, rode de novo com --aplicar.'); return 0

    py = [sys.executable, '-I']
    for etapa in (['tools/vigia.py', 'atualizar', arq], ['tools/vigia.py', 'build']):
        r = sh(py + etapa, repo); print(r.stdout[-1500:]);
        if r.returncode: print('FALHOU:', etapa[1], r.stderr[-500:]); return desfazer(repo)
    r = sh(py + ['tools/sincronia.py'], repo); print(r.stdout[-1500:])
    if r.returncode: print('SINCRONIA com ERRO: nada foi publicado, alteração local desfeita (CSV mantido).'); return desfazer(repo)
    if a.sem_git: return 0
    sh(['git', 'add', 'dados', 'index.html', 'lojas', 'ofertas'], repo)
    c = sh(['git', 'commit', '-m', 'Conferência (celular) %s: %d preços' % (hoje.isoformat(), len(achados))], repo)
    if c.returncode: print('Nada novo para publicar.'); return 0
    sh(['git', 'pull', '--rebase'], repo); p = sh(['git', 'push', 'origin', 'main'], repo)
    print('PUBLICADO.' if p.returncode == 0 else 'push falhou:\n' + p.stderr[-500:]); return p.returncode


def desfazer(repo):
    sh(['git', 'checkout', '--', 'dados', 'index.html', 'lojas', 'ofertas'], repo); return 1


if __name__ == '__main__':
    sys.exit(main())

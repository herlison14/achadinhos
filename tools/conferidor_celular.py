#!/usr/bin/env python3
"""Conferidor de preços do Achadinhos do Binga, para rodar no celular (Termux).

Usa o IP da sua casa (as lojas bloqueiam servidores) para ler o preço atual de cada
oferta e alimentar o vigia (tools/vigia.py). Só biblioteca padrão do Python 3.

  python3 -I tools/conferidor_celular.py               # TESTE: lê, compara e CALIBRA; não grava nada
  python3 -I tools/conferidor_celular.py --aplicar     # grava, regenera o site, confere e publica (git push)

Proteções (todas testadas em tools/simulador_celular.py):
  * CALIBRAÇÃO: o teste compara o que o celular lê com o preço já registrado. Só as lojas em que a leitura
    bate (>= 70% dentro de 2%) são liberadas para --aplicar. Sem teste prévio, --aplicar se recusa a rodar.
    Isso evita gravar o preço de tabela quando o site usa o preço no Pix (ou o contrário).
  * só entra preço realmente lido; variação maior que 25% NÃO é gravada (vai para o relatório);
  * item que está num post/Story agendado (a legenda e o card trazem o preço): se o preço mudou, fica PRESO
    para a rotina do Claude corrigir legenda e card; se não mudou, só renova a data de conferência;
  * Shopee, AliExpress e adidas ficam de fora (navegador logado / termos proíbem leitura automática);
  * não clica no link de afiliado a cada conferência: Amazon e Awin são lidos pela página da loja; link curto
    (meli.la) é aberto uma única vez por item e o destino fica no cache local;
  * só publica se `sincronia.py` terminar sem ERRO; se o push for recusado (outro robô publicou antes), refaz tudo
    sobre a versão nova; se falhar, desfaz a alteração local e mantém o CSV;
  * grava dados/celular.json (só contagens) para o painel/auditor saberem se o celular está vivo.
"""
import argparse, csv, datetime, gzip, json, os, random, re, subprocess, sys, time, traceback, zlib
import urllib.error, urllib.parse, urllib.request

UA = ('Mozilla/5.0 (Linux; Android 13; SM-G780G) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0.0.0 Mobile Safari/537.36')
FORA = {'shopee', 'aliexpress', 'adidas'}  # navegador logado / ambíguos / termos da adidas proíbem leitura automática
LIMITE_VARIACAO = 0.25                     # acima disso: não grava, só avisa (padrão; ajustável por --limite-variacao)
LIMITE = [LIMITE_VARIACAO]
TOLERANCIA_CALIBRACAO = 0.02               # leitura "bate" se estiver a até 2% do preço registrado
TAXA_MINIMA = 0.70                         # % de leituras que precisam bater para liberar a loja
HOME = os.path.expanduser('~')
CACHE = os.path.join(HOME, '.achadinhos_cache_urls.json')
CALIBRACAO = os.path.join(HOME, '.achadinhos_calibracao.json')
SAIDA = os.path.join(HOME, 'achadinhos-saida')
TIMEOUT = 20


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


def buscar(url, timeout=None):
    """GET com cabeçalhos de celular. Devolve (url_final, texto)."""
    req = urllib.request.Request(url, headers={
        'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml', 'Accept-Language': 'pt-BR,pt;q=0.9',
        'Accept-Encoding': 'gzip, deflate'})
    try:
        with urllib.request.urlopen(req, timeout=timeout or TIMEOUT) as r:
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
            if p is not None: saida.append((para_float(p), str(d.get('availability', '')), d.get('highPrice')))
        for k in ('offers', 'hasVariant', '@graph', 'mainEntity', 'item'):
            if k in d: _ofertas(d[k], saida)


def preco_jsonld(t):
    ofs = []
    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', t, re.S | re.I):
        try: _ofertas(json.loads(m.group(1).strip()), ofs)
        except ValueError: continue
    ofs = [o for o in ofs if o[0]]
    if not ofs: return None, 'sem_dado'
    if all('OutOfStock' in a or 'SoldOut' in a for _, a, _ in ofs): return None, 'sem_estoque'
    vivos = [o for o in ofs if not ('OutOfStock' in o[1] or 'SoldOut' in o[1])]
    precos = {p for p, _, _ in vivos}
    if any(h is not None and para_float(h) and para_float(h) != p for p, _, h in vivos): return None, 'ambiguo'
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
    m = re.search(r'priceToPay[^>]*>.*?a-offscreen[^>]*>\s*R\$(?:&nbsp;|\s|\xa0)*([\d.]+,\d{2})', t, re.S)
    if m: return num(m.group(1)), 'ok'
    if 'id="outofstock"' in low or 'não disponível no momento' in low: return None, 'sem_estoque'
    return None, 'sem_dado'


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
        url = urllib.parse.parse_qs(p.query).get('ued', [None])[0]
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


# ---------- seleção e classificação ----------
def posts_ativos(posts):
    """id do item -> True, para itens citados em post/Story agendado ou planejado (legenda e card trazem o preço)."""
    ids = set()
    for p in posts:
        if p.get('status') in ('agendado', 'planejado'): ids.update(p.get('produtos') or [])
    return ids


def escolher(itens, posts, limite, lojas, hoje):
    prox = set()
    for p in posts:
        if p.get('status') in ('agendado', 'planejado') and p.get('produtos'):
            try: d = datetime.date.fromisoformat(p['data'])
            except (KeyError, ValueError): continue
            if 0 <= (d - hoje).days <= 3: prox.update(p['produtos'])
    cand = [i for i in itens if i['loja'] not in FORA and (not lojas or i['loja'] in lojas)]
    cand.sort(key=lambda i: (i['id'] not in prox, i['conferido']))
    return cand[:limite]


def classificar(it, preco, ativos):
    reg = num(it['preco']); var = preco / reg - 1
    if abs(var) > LIMITE[0]: return 'suspeito', var
    if fmt(preco) == it['preco']: return 'igual', var
    if it['id'] in ativos: return 'preso', var
    return 'mudou', var


def calibrar(leituras):
    """Por loja: quantas leituras batem (até 2%) com o preço registrado."""
    por = {}
    for it, preco, _ in leituras:
        n, k = por.get(it['loja'], (0, 0))
        por[it['loja']] = (n + 1, k + (1 if abs(preco / num(it['preco']) - 1) <= TOLERANCIA_CALIBRACAO else 0))
    return por


def ler_json(p, pad):
    try:
        with open(p, encoding='utf-8') as f: return json.load(f)
    except (OSError, ValueError): return pad


# ---------- git / execução ----------
def sh(args, cwd, **kw):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, **kw)


def preparar_repo(repo):
    """Árvore limpa + versão mais nova do GitHub. Devolve (ok, mensagem)."""
    f = sh(['git', 'fetch', 'origin', 'main'], repo)
    if f.returncode: return False, 'sem conexão com o GitHub (git fetch falhou): ' + f.stderr.strip()[-200:]
    r = sh(['git', 'reset', '--hard', 'origin/main'], repo)
    if r.returncode: return False, 'git reset falhou: ' + r.stderr.strip()[-200:]
    sh(['git', 'clean', '-fdq'], repo)
    return True, ''


def desfazer(repo, sem_git):
    if sem_git: sh(['git', 'checkout', '--', '.'], repo)
    else: sh(['git', 'reset', '--hard'], repo); sh(['git', 'clean', '-fdq'], repo)
    return 1


def etapas(repo, arq, estado):
    """atualizar + build + status + sincronia. Devolve 0 ou o código de falha."""
    py = [sys.executable, '-I']
    for e in (['tools/vigia.py', 'atualizar', arq], ['tools/vigia.py', 'build']):
        r = sh(py + e, repo); print(r.stdout[-1200:])
        if r.returncode: print('FALHOU:', e[1], r.stderr[-400:]); return 1
    with open(os.path.join(repo, 'dados', 'celular.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(estado, f, ensure_ascii=False, indent=1); f.write('\n')
    r = sh(py + ['tools/sincronia.py'], repo); print(r.stdout[-1200:])
    if r.returncode: print('SINCRONIA com ERRO: nada será publicado.'); return 2
    return 0


def escrever_csv(arq, aplic, hoje, repo, refeito):
    """CSV id;preco;data. Em nova tentativa, descarta linha de item que OUTRO robô já atualizou (o dado mais novo vence)."""
    atual = {i['id']: i['preco'] for i in ler_json(os.path.join(repo, 'dados/itens.json'), [])} if refeito else {}
    n = 0
    with open(arq, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(['id', 'preco', 'data'])
        for it, pr, _, _ in aplic:
            if refeito and atual.get(it['id'], it['preco']) != it['preco']:
                print('  outro robô já atualizou "%s" (R$ %s): mantido o dado dele.' % (it['nome'][:40], atual[it['id']])); continue
            w.writerow([it['id'], pr, br(hoje)]); n += 1
    return n


def aplicar_e_publicar(repo, arq, hoje, aplic, estado, sem_git):
    for tentativa in range(1, 5):
        if tentativa > 1 and not sem_git:
            ok, msg = preparar_repo(repo)
            if not ok: print(msg); return 2
        n = escrever_csv(arq, aplic, hoje, repo, tentativa > 1)
        rc = etapas(repo, arq, estado)
        if rc: desfazer(repo, sem_git); print('Alteração local desfeita (CSV mantido: %s).' % arq); return rc
        if sem_git: return 0
        sh(['git', 'add', '-A'], repo)
        c = sh(['git', 'commit', '-m', 'Conferência (celular) %s: %d preços' % (hoje.isoformat(), n)], repo)
        if c.returncode: print('Nada novo para publicar.'); return 0
        p = sh(['git', 'push', 'origin', 'main'], repo)
        if p.returncode == 0: print('PUBLICADO (tentativa %d).' % tentativa); return 0
        print('push recusado (outro robô publicou antes); refazendo sobre a versão nova (tentativa %d)...' % tentativa)
    print('Não consegui publicar após 4 tentativas; nada foi alterado no GitHub (tento de novo na próxima rodada).'); desfazer(repo, sem_git); return 2


def main(argv=None):
    ap = argparse.ArgumentParser(description='Conferidor de preços (celular)')
    ap.add_argument('--repo', default=None, help='pasta do repositório (padrão: a do script ou a atual)')
    ap.add_argument('--limite', type=int, default=40, help='itens por rodada (padrão 40)')
    ap.add_argument('--lojas', default='', help='só estas lojas, ex.: amazon,magalu')
    ap.add_argument('--aplicar', action='store_true', help='grava, regenera, confere e publica (exige teste prévio)')
    ap.add_argument('--sem-git', action='store_true', help='só para testes: não faz fetch/commit/push')
    ap.add_argument('--limite-variacao', type=float, default=0.25, help='variação máxima aceita sozinha (0,25 = 25%%); acima disso vai para conferir à mão')
    a = ap.parse_args(argv)
    LIMITE[0] = a.limite_variacao
    aqui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo = a.repo or (aqui if os.path.exists(os.path.join(aqui, 'dados', 'itens.json')) else os.getcwd())
    if not os.path.exists(os.path.join(repo, 'dados', 'itens.json')): print('Não achei dados/itens.json em ' + repo); return 1
    agora = datetime.datetime.now().astimezone()
    print('=== %s | %s ===' % (agora.strftime('%d/%m/%Y %H:%M'), 'APLICAR' if a.aplicar else 'TESTE (nada será gravado)'))

    cal = ler_json(CALIBRACAO, {})
    if a.aplicar:
        if not cal: print('Rode primeiro o TESTE (sem --aplicar): ele calibra quais lojas o celular lê direito.'); return 1
        if not a.sem_git:
            if sh(['git', 'status', '--porcelain', '--untracked-files=no'], repo).stdout.strip():
                print('Há alterações locais no repositório do celular; não vou mexer. Rode: git -C %s status' % repo); return 1
            ok, msg = preparar_repo(repo)
            if not ok: print(msg, '\nNada feito; tento de novo na próxima rodada.'); return 2

    itens, posts = ler_json(os.path.join(repo, 'dados/itens.json'), []), ler_json(os.path.join(repo, 'dados/posts.json'), [])
    cache = ler_json(CACHE, {})
    hoje = agora.date(); ativos = posts_ativos(posts)
    lojas = {x.strip() for x in a.lojas.split(',') if x.strip()}
    lista = escolher(itens, posts, a.limite, lojas, hoje)
    print('Conferindo %d itens\n' % len(lista))

    leituras, pend, resumo, bloqueios, ultimo = [], [], {}, {}, {}
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
            ultimo[loja] = time.time(); anota('erro'); print('  [%s] erro (%s): %s' % (loja, type(e).__name__, it['nome'][:40])); continue
        if preco is None:
            anota(estado)
            if estado == 'sem_estoque': pend.append('SEM ESTOQUE: [%s] %s (id %s)' % (loja, it['nome'][:45], it['id']))
            continue
        leituras.append((it, preco, classificar(it, preco, ativos)))

    json.dump(cache, open(CACHE, 'w'))
    # ---- calibração por loja
    por = calibrar([(i, p, c) for i, p, c in leituras]); novo_cal = dict(cal); live_ruim = set()
    for loja, (n, k) in por.items():
        taxa = k / n if n else 0; reg = {'n': n, 'bateu': k, 'taxa': round(taxa, 2), 'data': hoje.isoformat()}
        if not a.aplicar:
            if n >= 3: novo_cal[loja] = dict(reg, liberada=taxa >= TAXA_MINIMA)
        elif loja in cal and cal[loja].get('liberada') and n >= 5 and taxa < 0.5:
            live_ruim.add(loja); novo_cal[loja] = dict(reg, liberada=False)      # a loja mudou de layout/preço: trava até novo teste
        elif loja not in cal and n >= 8 and taxa >= 0.8:
            novo_cal[loja] = dict(reg, liberada=True, auto=True)                  # loja nova na fila: libera para a PRÓXIMA rodada
    if novo_cal != cal: json.dump(novo_cal, open(CALIBRACAO, 'w'))
    ref = novo_cal if not a.aplicar else {k: v for k, v in cal.items() if k not in live_ruim}   # na rodada valem as liberações anteriores
    liberadas = {l for l, c in ref.items() if c.get('liberada')}

    # ---- decisão por item
    aplic = []; cont = {'igual': 0, 'mudou': 0, 'preso': 0, 'suspeito': 0, 'nao_calibrada': 0}
    for it, preco, (cls, var) in leituras:
        loja = it['loja']; r = resumo[loja]
        if cls == 'suspeito':
            pend.append('CONFERIR À MÃO: [%s] %s: registrado R$ %s, lido R$ %s (%+.0f%%)' % (loja, it['nome'][:40], it['preco'], fmt(preco), var * 100))
        elif cls == 'preso':
            pend.append('PRESO (post agendado traz o preço): [%s] %s: R$ %s -> R$ %s' % (loja, it['nome'][:40], it['preco'], fmt(preco)))
        elif loja not in liberadas:
            cls = 'nao_calibrada'
        else:
            aplic.append((it, fmt(preco), cls, var))
        r[cls] = r.get(cls, 0) + 1; cont[cls] = cont.get(cls, 0) + 1
        if cls == 'mudou': print('  [%s] %+.1f%%  %s: %s -> %s' % (loja, var * 100, it['nome'][:40], it['preco'], fmt(preco)))

    print('\nResumo por loja:')
    for loja, r in sorted(resumo.items()):
        c = ref.get(loja) or novo_cal.get(loja)
        sel = '' if not c else ('  [calibração %d%%: %s]' % (c['taxa'] * 100, 'LIBERADA' if c['liberada'] else 'NÃO liberada'))
        print('  %-10s %s%s' % (loja, ', '.join('%s %d' % (k, v) for k, v in sorted(r.items())), sel))
    for p in pend[:25]: print('  !', p)
    print('\nLidos: %d de %d | aplicáveis: %d | presos: %d | suspeitos: %d | lojas ainda não calibradas: %d leituras' % (
        len(leituras), len(lista), len(aplic), cont['preso'], cont['suspeito'], cont['nao_calibrada']))
    print('Shopee, AliExpress e adidas continuam na rotina do computador.')

    if not a.aplicar:
        print('\nTeste concluído (calibração salva). Lojas liberadas: %s.' % (', '.join(sorted(liberadas)) or 'nenhuma'))
        print('Se está de acordo, rode com --aplicar.'); return 0

    estado = {'ultima_execucao': agora.isoformat(timespec='minutes'), 'lidos': len(leituras), 'aplicados': len(aplic),
              'presos': cont['preso'], 'suspeitos': cont['suspeito'], 'nao_calibrados': cont['nao_calibrada'],
              'bloqueios': {l: n for l, n in bloqueios.items() if n}, 'lojas_liberadas': sorted(liberadas)}
    for l in live_ruim: print('ATENÇÃO: leitura de %s deixou de bater com o registrado; loja bloqueada até novo teste.' % l)
    aplic = [x for x in aplic if x[0]['loja'] not in live_ruim]
    estado['aplicados'] = len(aplic)
    os.makedirs(SAIDA, exist_ok=True)
    arq = os.path.join(SAIDA, 'precos_%s.csv' % hoje.isoformat())
    print('CSV:', arq)
    return aplicar_e_publicar(repo, arq, hoje, aplic, estado, a.sem_git)


if __name__ == '__main__':
    try: sys.exit(main())
    except KeyboardInterrupt: sys.exit(130)
    except Exception:
        print('ERRO INESPERADO (nada foi publicado):'); traceback.print_exc(); sys.exit(1)

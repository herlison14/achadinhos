#!/usr/bin/env python3
"""Simulador do conferidor de preços do celular (ambiente de teste, sem tocar em nada real).

Monta, numa pasta temporária: um GitHub falso (repositório bare local), o clone do "celular", o clone de outro
"escritor" (PC/robôs da nuvem), uma pasta HOME de Termux e um servidor de lojas falsas (Amazon, Magalu, Mercado
Livre e lojas Awin) que imita captcha, bloqueio, timeout, produto esgotado, preço de tabela x Pix etc.
Depois roda o conferidor de verdade (o mesmo código) em cada cenário e confere o resultado.

  python3 -I tools/simulador_celular.py            # roda todos os cenários
  python3 -I tools/simulador_celular.py S2 S5      # só alguns

O que ele NÃO prova: se as lojas reais aceitam o celular e se os trechos de HTML reais batem com os extratores.
Isso só o teste (modo sem --aplicar) no celular de verdade responde.
"""
import contextlib, datetime, http.server, io, json, os, re, shutil, subprocess, sys, tempfile, threading, time, urllib.parse, urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))
import conferidor_celular as c

REAL_URLOPEN = urllib.request.urlopen
RES, ESTADO, SLEEP = [], {}, [0.0]


def chk(nome, cond, detalhe=''):
    RES.append((nome, bool(cond), detalhe)); print('   %s %s%s' % ('OK ' if cond else 'FALHA', nome, ('  -> ' + str(detalhe)) if (detalhe and not cond) else ''))


def git(cwd, *a, check=True):
    r = subprocess.run(['git'] + list(a), cwd=cwd, text=True, capture_output=True)
    if check and r.returncode: raise RuntimeError('git %s: %s' % (a, r.stderr))
    return r.stdout.strip()


# ---------- lojas falsas ----------
class Lojas(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path); partes = u.path.split('/', 3)       # ['', '__h', host, resto]
        host, resto = partes[2], '/' + (partes[3] if len(partes) > 3 else '')
        ESTADO['hits'].append((host, resto + ('?' + u.query if u.query else '')))
        if host == 'meli.la':
            alvo = ESTADO['meli_curto'].get(resto.strip('/'))
            if not alvo: return self.responder(404, 'x')
            self.send_response(302); self.send_header('Location', 'http://127.0.0.1:%d/__h/%s?abc=1' % (ESTADO['porta'], alvo)); self.end_headers(); return
        it = ESTADO['registro'].get(host + resto)
        if not it: return self.responder(404, '<html>não achei</html>')
        modo = ESTADO['modo'](it)
        if modo == 'captcha': return self.responder(200, '<html>Digite os caracteres que você vê captcha</html>')
        if modo in ('403', '429', '503'): return self.responder(int(modo), 'bloqueado')
        if modo == '500': return self.responder(500, 'erro')
        if modo == 'lento': threading.Event().wait(2.5)
        self.responder(200, self.pagina(it, modo))

    def responder(self, cod, corpo):
        b = corpo.encode(); self.send_response(cod); self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(b))); self.end_headers()
        try: self.wfile.write(b)
        except OSError: pass

    def pagina(self, it, modo):
        p = ESTADO['preco'](it); loja = it['loja']; br = c.fmt(p); en = '%.2f' % p
        if loja == 'amazon':
            if modo == 'esgotado': return '<html><div id="outOfStock">Não disponível no momento</div></html>'
            if modo == 'sem_dado': return '<html>sem preço aqui</html>'
            return '<html><div class="a-section priceToPay"><span class="a-offscreen">R$&nbsp;%s</span></div></html>' % br
        if loja == 'magalu':
            if modo == 'sem_dado': return '<html>só texto</html>'
            return '<html><span>R$ %s</span> <small>no Pix</small> <s>R$ %s</s></html>' % (br, c.fmt(p * 1.1))
        if modo == 'sem_dado': return '<html>nada</html>'
        disp = 'https://schema.org/OutOfStock' if (modo == 'esgotado' or loja == 'dafiti') else 'https://schema.org/InStock'
        if modo == 'ambiguo':
            of = {'@type': 'AggregateOffer', 'lowPrice': en, 'highPrice': '%.2f' % (p * 1.5), 'availability': disp}
        elif loja in ('reserva', 'cea'):
            of = [{'@type': 'Offer', 'price': en, 'availability': disp}] * 3
        else:
            of = {'@type': 'Offer', 'price': (float(en) if loja == 'lauri' else en), 'availability': disp}
        return '<html><script type="application/ld+json">%s</script></html>' % json.dumps({'@context': 'https://schema.org', '@type': 'Product', 'name': it['nome'], 'offers': of})


def urlopen_falso(req, timeout=None):
    url = req.full_url if hasattr(req, 'full_url') else req
    p = urllib.parse.urlparse(url)
    if p.netloc.startswith('127.0.0.1'): url = re.sub(r'^http://127\.0\.0\.1:\d+', 'http://127.0.0.1:%d' % ESTADO['porta'], url)   # cache guarda o destino já reescrito
    else: url = 'http://127.0.0.1:%d/__h/%s%s%s' % (ESTADO['porta'], p.netloc, p.path, '?' + p.query if p.query else '')
    req = urllib.request.Request(url, headers=dict(req.header_items()) if hasattr(req, 'header_items') else {})
    return REAL_URLOPEN(req, timeout=timeout)


# ---------- ambiente ----------
def chave_de(it):
    h = it['href']; p = urllib.parse.urlparse(h)
    if 'awin1.com' in p.netloc:
        q = urllib.parse.urlparse(urllib.parse.parse_qs(p.query)['ued'][0]); return q.netloc + q.path
    if it['loja'] == 'amazon':
        return 'www.amazon.com.br/dp/' + re.search(r'/dp/([A-Z0-9]{10})', h).group(1)
    if it['loja'] == 'magalu': return p.netloc + p.path
    if it['loja'] == 'meli': return 'produto.mercadolivre.com.br/MLB-%s-produto' % it['id']
    return None


class Ambiente:
    def __init__(self, semente):
        self.t = tempfile.mkdtemp(prefix='sim_celular_')
        self.remoto = os.path.join(self.t, 'remoto.git'); self.cel = os.path.join(self.t, 'celular'); self.pc = os.path.join(self.t, 'pc')
        self.home = os.path.join(self.t, 'home'); os.makedirs(self.home)
        shutil.copytree(semente, os.path.join(self.t, 'semente_cp'))   # semente.git local reaproveitado
        subprocess.run(['git', 'clone', '-q', '--bare', os.path.join(self.t, 'semente_cp'), self.remoto], check=True)
        for d in (self.cel, self.pc):
            subprocess.run(['git', 'clone', '-q', self.remoto, d], check=True)
            git(d, 'config', 'user.email', 'sim@teste'); git(d, 'config', 'user.name', 'sim')
        c.CACHE = os.path.join(self.home, 'cache.json'); c.CALIBRACAO = os.path.join(self.home, 'cal.json'); c.SAIDA = os.path.join(self.home, 'saida')
        c.TIMEOUT = 1.2; self.itens = json.load(open(os.path.join(self.cel, 'dados/itens.json'), encoding='utf-8'))
        reg, curto = {}, {}
        for it in self.itens:
            k = chave_de(it)
            if k: reg[k] = it
            if it['loja'] == 'meli': curto[it['href'].rstrip('/').split('/')[-1]] = 'produto.mercadolivre.com.br/MLB-%s-produto' % it['id']
        ESTADO.update(registro=reg, meli_curto=curto, hits=[], modo=lambda it: 'ok', preco=lambda it: c.num(it['preco']))

    def limpar(self): shutil.rmtree(self.t, ignore_errors=True)
    def remoto_head(self): return git(self.remoto, 'rev-parse', 'main')


def semente_de(origem):
    """Cópia dos arquivos versionados num repositório novo (sem histórico, rápido)."""
    d = tempfile.mkdtemp(prefix='semente_'); arqs = git(origem, 'ls-files').splitlines()
    for a in arqs:
        dest = os.path.join(d, a); os.makedirs(os.path.dirname(dest), exist_ok=True); shutil.copy2(os.path.join(origem, a), dest)
    git(d, 'init', '-q', '-b', 'main'); git(d, 'config', 'user.email', 's@s'); git(d, 'config', 'user.name', 's')
    git(d, 'add', '-A'); git(d, 'commit', '-q', '-m', 'semente'); return d


def rodar(amb, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try: rc = c.main(['--repo', amb.cel] + list(args))
        except SystemExit as e: rc = e.code
    return rc, buf.getvalue()


def ids_ativos(amb):
    return c.posts_ativos(json.load(open(os.path.join(amb.cel, 'dados/posts.json'), encoding='utf-8')))


def item(amb, i): return next(x for x in json.load(open(os.path.join(amb.cel, 'dados/itens.json'), encoding='utf-8')) if x['id'] == i)


def amostra(amb, loja_nao=(), em_post=False, n=3, lojas=None):
    at = ids_ativos(amb)
    return [x for x in amb.itens if x['loja'] not in c.FORA and x['loja'] not in loja_nao and ((x['id'] in at) == em_post)
            and (not lojas or x['loja'] in lojas)][:n]


def preco_com(mods):
    return lambda it: c.num(it['preco']) * mods.get(it['id'], 1.0)


def hoje_br(): return datetime.date.today().isoformat()


# ---------- cenários ----------
def S0(amb):
    """--aplicar sem teste prévio"""
    h0 = amb.remoto_head(); rc, out = rodar(amb, '--aplicar', '--limite', '10')
    chk('recusa rodar sem calibração', rc == 1 and 'Rode primeiro o TESTE' in out, out[-200:]); chk('nada publicado', amb.remoto_head() == h0)


def S1(amb):
    """teste (dry-run): calibra e não grava nada"""
    h0 = amb.remoto_head(); rc, out = rodar(amb, '--limite', '500')
    cal = json.load(open(c.CALIBRACAO)); lib = sorted(l for l, v in cal.items() if v['liberada'])
    chk('rc 0', rc == 0, out[-300:]); chk('nada publicado', amb.remoto_head() == h0)
    chk('árvore limpa depois do teste', git(amb.cel, 'status', '--porcelain') == '', git(amb.cel, 'status', '--porcelain'))
    chk('todas as lojas lidas foram liberadas (lojas fiéis ao registrado)', len(lib) >= 12, lib)
    chk('Shopee/AliExpress/adidas nunca lidas', not any(h[0] in ('s.shopee.com.br', 's.click.aliexpress.com') for h in ESTADO['hits']))
    print('   lojas liberadas:', ', '.join(lib))


def calibrar_normal(amb): rodar(amb, '--limite', '500')


def S2(amb):
    """aplicar: mudou / preso / suspeito / igual-em-post"""
    calibrar_normal(amb); at = ids_ativos(amb)
    livres = amostra(amb, n=12); postados = amostra(amb, em_post=True, n=8)
    mods = {}
    for it in livres[:6]: mods[it['id']] = 0.9            # queda 10% fora de post -> aplica
    for it in postados[:3]: mods[it['id']] = 0.9          # queda 10% em post agendado -> PRESO
    for it in livres[6:8]: mods[it['id']] = 2.0           # +100% -> suspeito
    ESTADO['preco'] = preco_com(mods); h0 = amb.remoto_head()
    from_texto = lambda: subprocess.run([sys.executable, '-I', 'tools/instagram.py', 'testar'], cwd=amb.cel, text=True, capture_output=True)
    antes = from_texto()
    rc, out = rodar(amb, '--aplicar', '--limite', '500')
    chk('rc 0', rc == 0, out[-400:]); chk('um commit novo no GitHub', git(amb.remoto, 'rev-list', '--count', 'main') == str(int(git(amb.remoto, 'rev-list', '--count', h0)) + 1))
    chk('PUBLICADO', 'PUBLICADO' in out, out[-300:]); chk('sincronia OK', 'SINCRONIA: OK' in out)
    novo = {x['id']: x for x in json.load(open(os.path.join(amb.cel, 'dados/itens.json'), encoding='utf-8'))}
    chk('queda fora de post gravada', all(novo[i['id']]['preco'] == c.fmt(c.num(i['preco']) * 0.9) for i in livres[:6]), [(i['id'], novo[i['id']]['preco'], i['preco']) for i in livres[:6]][:2])
    chk('preço em post agendado NÃO muda (preso)', all(novo[i['id']]['preco'] == i['preco'] for i in postados[:3]))
    chk('+100% NÃO gravado (suspeito)', all(novo[i['id']]['preco'] == i['preco'] for i in livres[6:8]))
    chk('item em post com preço igual renova a data', all(novo[i['id']]['conferido'] == hoje_br() for i in postados[3:8]))
    hb = json.load(open(os.path.join(amb.cel, 'dados/celular.json')))
    chk('heartbeat dados/celular.json gravado', hb['lidos'] > 100 and hb['presos'] == 3 and hb['suspeitos'] == 2, hb)
    chk('árvore limpa depois de publicar', git(amb.cel, 'status', '--porcelain') == '')
    depois = from_texto()
    cnt = lambda s: len(re.findall(r'bloquead|ERRO|não traz o preço', s.stdout + s.stderr, re.I))
    chk('o celular não criou novos bloqueios no publicador (testar)', cnt(depois) <= cnt(antes), 'antes %d depois %d' % (cnt(antes), cnt(depois)))
    print('   instagram.py testar, últimas linhas:', (depois.stdout or depois.stderr).strip().splitlines()[-2:])
    aud = subprocess.run([sys.executable, '-I', 'tools/auditor.py', '--sem-github'], cwd=amb.cel, text=True, capture_output=True)
    chk('auditor roda sem erro depois do celular', aud.returncode in (0, 1) and 'Traceback' not in aud.stderr, aud.stderr[-300:])


def S3(amb):
    """preço de tabela em vez do Pix (nike/kabum +8%)"""
    ESTADO['preco'] = lambda it: c.num(it['preco']) * (1.08 if it['loja'] in ('nike', 'kabum') else 1.0)
    rodar(amb, '--limite', '500'); cal = json.load(open(c.CALIBRACAO))
    chk('nike e kabum NÃO liberadas', not cal['nike']['liberada'] and not cal['kabum']['liberada'], {k: cal[k] for k in ('nike', 'kabum')})
    chk('outras lojas liberadas', cal['amazon']['liberada'] and cal['magalu']['liberada'])
    rc, out = rodar(amb, '--aplicar', '--limite', '500'); novo = json.load(open(os.path.join(amb.cel, 'dados/itens.json'), encoding='utf-8'))
    ant = {x['id']: x for x in amb.itens}
    chk('nenhum preço de nike/kabum foi gravado', all(x['preco'] == ant[x['id']]['preco'] for x in novo if x['loja'] in ('nike', 'kabum')))


def S4(amb):
    """Amazon devolve captcha"""
    calibrar_normal(amb); ESTADO['hits'].clear()
    ESTADO['modo'] = lambda it: 'captcha' if it['loja'] == 'amazon' else 'ok'
    rc, out = rodar(amb, '--aplicar', '--limite', '500'); az = [h for h in ESTADO['hits'] if h[0] == 'www.amazon.com.br']
    chk('parou de insistir na Amazon após 3 bloqueios', len(az) == 3, len(az)); chk('demais lojas seguiram', 'PUBLICADO' in out or 'Nada novo' in out, out[-300:])
    novo = json.load(open(os.path.join(amb.cel, 'dados/itens.json'), encoding='utf-8')); ant = {x['id']: x for x in amb.itens}
    chk('nenhum preço da Amazon foi alterado', all(x['preco'] == ant[x['id']]['preco'] and x['conferido'] == ant[x['id']]['conferido'] for x in novo if x['loja'] == 'amazon'))


def S5(amb):
    """outro robô publica no meio do push (corrida)"""
    calibrar_normal(amb); livres = amostra(amb, n=8); ESTADO['preco'] = preco_com({i['id']: 0.9 for i in livres[:4]})
    original = c.sh; usado = [False]; outro = livres[7]

    def sh_com_corrida(args, cwd, **kw):
        if args[:2] == ['git', 'push'] and not usado[0]:
            usado[0] = True
            p = os.path.join(amb.pc, 'dados/itens.json'); d = json.load(open(p, encoding='utf-8'))
            for x in d:
                if x['id'] == outro['id']: x['preco'] = '9,99'
            json.dump(d, open(p, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1); open(p, 'a').write('\n')
            git(amb.pc, 'commit', '-qam', 'robô da nuvem mexeu em outro item'); git(amb.pc, 'push', '-q', 'origin', 'main')
        return original(args, cwd, **kw)
    c.sh = sh_com_corrida
    try: rc, out = rodar(amb, '--aplicar', '--limite', '500')
    finally: c.sh = original
    novo = {x['id']: x for x in json.load(open(os.path.join(amb.cel, 'dados/itens.json'), encoding='utf-8'))}
    chk('push recusado e refeito sobre a versão nova', 'refazendo' in out and 'PUBLICADO (tentativa 2)' in out, out[-400:])
    chk('mudança do outro robô preservada', novo[outro['id']]['preco'] == '9,99'); chk('nossas quedas também chegaram', all(novo[i['id']]['preco'] != i['preco'] for i in livres[:4]))
    chk('GitHub tem os dois commits', 'robô da nuvem' in git(amb.remoto, 'log', '--format=%s', '-3') and 'Conferência (celular)' in git(amb.remoto, 'log', '--format=%s', '-3'))


def S6(amb):
    """sincronia acusa ERRO"""
    calibrar_normal(amb); ESTADO['preco'] = preco_com({i['id']: 0.9 for i in amostra(amb, n=4)}); h0 = amb.remoto_head(); original = c.sh

    def sh_ruim(args, cwd, **kw):
        if any('sincronia.py' in str(a) for a in args): return subprocess.CompletedProcess(args, 1, 'ERRO: simulado', '')
        return original(args, cwd, **kw)
    c.sh = sh_ruim
    try: rc, out = rodar(amb, '--aplicar', '--limite', '500')
    finally: c.sh = original
    chk('rc 2 e nada publicado', rc == 2 and amb.remoto_head() == h0, (rc, out[-200:])); chk('alteração local desfeita', git(amb.cel, 'status', '--porcelain') == '')
    chk('CSV mantido para análise', any(f.endswith('.csv') for f in os.listdir(c.SAIDA)))


def S7(amb):
    """GitHub inacessível"""
    calibrar_normal(amb); os.rename(amb.remoto, amb.remoto + '_fora')
    rc, out = rodar(amb, '--aplicar', '--limite', '50'); os.rename(amb.remoto + '_fora', amb.remoto)
    chk('rc 2, mensagem clara, sem traceback', rc == 2 and 'sem conexão com o GitHub' in out and 'Traceback' not in out, out[-300:])


def S8(amb):
    """internet/lojas fora do ar (conexão recusada)"""
    calibrar_normal(amb); porta_certa = ESTADO['porta']; ESTADO['porta'] = 1   # nada escuta na porta 1
    rc, out = rodar(amb, '--aplicar', '--limite', '60'); ESTADO['porta'] = porta_certa
    chk('não quebra: 0 lidos, heartbeat registra', rc == 0 and 'Lidos: 0' in out, (rc, out[-300:]))
    hb = json.load(open(os.path.join(amb.cel, 'dados/celular.json'))); chk('heartbeat mostra 0 lidos (aparece no painel)', hb['lidos'] == 0, hb)
    chk('nenhum preço mudou', 'atualizados: 0 mudaram' in out)


def S9(amb):
    """lojas lentas e com erro 500"""
    calibrar_normal(amb); alvos = amostra(amb, n=6)
    ESTADO['modo'] = lambda it: 'lento' if it['id'] in {a['id'] for a in alvos[:2]} else ('500' if it['id'] in {a['id'] for a in alvos[2:4]} else 'ok')
    t0 = time.time(); rc, out = rodar(amb, '--aplicar', '--limite', '500'); dt = time.time() - t0
    chk('terminou mesmo com timeouts/500', rc == 0 and 'erro (' in out, out[-300:]); chk('tempo limitado', dt < 40, '%.1fs' % dt)


def S10(amb):
    """repetição no mesmo dia, cache do link curto e cliques em afiliado"""
    calibrar_normal(amb); ESTADO['hits'].clear(); rc1, o1 = rodar(amb, '--aplicar', '--limite', '500')
    curtos1 = len([h for h in ESTADO['hits'] if h[0] == 'meli.la']); n = len([x for x in amb.itens if x['loja'] == 'meli'])
    rc2, o2 = rodar(amb, '--aplicar', '--limite', '500'); curtos2 = len([h for h in ESTADO['hits'] if h[0] == 'meli.la']) - curtos1
    chk('segunda rodada do dia não quebra', rc2 == 0, o2[-300:]); chk('nenhuma mudança de preço na repetição', 'atualizados: 0 mudaram' in o2)
    chk('link curto do ML aberto no máximo 1x por item (calibração já tinha feito o cache)', curtos1 == 0 and curtos2 == 0, (curtos1, curtos2, n))
    chk('nenhum acesso a awin1.com nem a URL com tag= de afiliado', not any(h[0] == 'awin1.com' or 'tag=' in h[1] for h in ESTADO['hits']), [h for h in ESTADO['hits'] if 'tag=' in h[1]][:2])


def S11(amb):
    """páginas estranhas: esgotado, ambíguo, sem dado, Dafiti esgotado por robô"""
    calibrar_normal(amb); a = amostra(amb, n=60); mapa = {}
    ids = {'esgotado': a[0], 'ambiguo': a[1], 'sem_dado': a[2]}
    ESTADO['modo'] = lambda it: next((m for m, x in ids.items() if x['id'] == it['id']), 'ok'); h0 = amb.remoto_head()
    rc, out = rodar(amb, '--limite', '500')   # teste, só relatório
    ant = {x['id']: x for x in amb.itens}
    chk('esgotado listado como SEM ESTOQUE (nunca remove sozinho)', 'SEM ESTOQUE' in out or ids['esgotado']['loja'] in ('magalu', 'dafiti'), out[-200:])
    chk('Dafiti esgotado-por-robô não vira alarme', 'SEM ESTOQUE: [dafiti]' not in out)
    chk('nada publicado em modo teste', amb.remoto_head() == h0)


def S12(amb):
    """repositório do celular com alteração local"""
    calibrar_normal(amb); p = os.path.join(amb.cel, 'CLAUDE.md'); open(p, 'a').write('\nminha anotação\n'); h0 = amb.remoto_head()
    rc, out = rodar(amb, '--aplicar', '--limite', '50')
    chk('recusa mexer e não perde a anotação', rc == 1 and 'minha anotação' in open(p).read() and amb.remoto_head() == h0, out[-200:])


def S13(amb):
    """quanto tempo de espera real (ritmo educado) para 120 itens"""
    calibrar_normal(amb); SLEEP[0] = 0; rodar(amb, '--aplicar', '--limite', '120')
    print('   espera acumulada de cortesia para 120 itens: %.1f min (+ tempo das páginas)' % (SLEEP[0] / 60)); chk('rodada de 120 itens cabe em ~15 min de espera', SLEEP[0] < 15 * 60, SLEEP[0])


def S14(amb):
    """queda grande de Black Friday (-30%) fora de post"""
    calibrar_normal(amb); livres = amostra(amb, n=6); ESTADO['preco'] = preco_com({i['id']: 0.7 for i in livres})
    rc, out = rodar(amb, '--aplicar', '--limite', '500'); novo = {x['id']: x for x in json.load(open(os.path.join(amb.cel, 'dados/itens.json'), encoding='utf-8'))}
    chk('quedas de 30% não são gravadas sozinhas (ficam para conferir à mão)', all(novo[i['id']]['preco'] == i['preco'] for i in livres) and out.count('CONFERIR À MÃO') >= 6, out[-300:])


def S15(amb):
    """controle negativo: sem a trava de 'preso', o publicador bloquearia posts"""
    at = ids_ativos(amb); it = next(x for x in amb.itens if x['id'] in at and x['loja'] not in c.FORA)
    csvp = os.path.join(amb.t, 'x.csv'); open(csvp, 'w').write('id;preco;data\n%s;%s;%s\n' % (it['id'], c.fmt(c.num(it['preco']) * 0.9), datetime.date.today().strftime('%d/%m/%Y')))
    subprocess.run([sys.executable, '-I', 'tools/vigia.py', 'atualizar', csvp], cwd=amb.cel, capture_output=True)
    r = subprocess.run([sys.executable, '-I', 'tools/instagram.py', 'testar'], cwd=amb.cel, text=True, capture_output=True)
    ruins = [l for l in (r.stdout + r.stderr).splitlines() if l.strip() and not l.rstrip().endswith('OK') and 'preço' in l]
    chk('mudar preço de item em post agendado, sem trava, BLOQUEIA o post (por isso o celular trava)', len(ruins) >= 1, (r.stdout + r.stderr)[-300:])


def S16(amb):
    """loja nova na fila: só é liberada para a rodada seguinte, depois de >=8 leituras fiéis"""
    rodar(amb, '--limite', '500', '--lojas', 'amazon,magalu'); cal0 = json.load(open(c.CALIBRACAO))
    alvo_loja = amostra(amb, n=12, lojas={'meli'}); ESTADO['preco'] = preco_com({i['id']: 0.9 for i in alvo_loja[:3]})
    rc, out = rodar(amb, '--aplicar', '--limite', '500'); cal1 = json.load(open(c.CALIBRACAO))
    novo = {x['id']: x for x in json.load(open(os.path.join(amb.cel, 'dados/itens.json'), encoding='utf-8'))}
    chk('antes só amazon e magalu estavam liberadas', set(cal0) == {'amazon', 'magalu'}, list(cal0))
    chk('meli entrou na calibração como liberada (auto) para a próxima rodada', cal1.get('meli', {}).get('liberada') and cal1['meli'].get('auto'), cal1.get('meli'))
    chk('mas nesta rodada nenhum preço de meli foi gravado', all(novo[i['id']]['preco'] == i['preco'] for i in alvo_loja))
    rc, out = rodar(amb, '--aplicar', '--limite', '500'); novo = {x['id']: x for x in json.load(open(os.path.join(amb.cel, 'dados/itens.json'), encoding='utf-8'))}
    chk('na rodada seguinte meli já é gravado', all(novo[i['id']]['preco'] == c.fmt(c.num(i['preco']) * 0.9) for i in alvo_loja[:3]), out[-200:])


CENARIOS = [S0, S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13, S14, S15, S16]


def main():
    escolhidos = [a.upper() for a in sys.argv[1:]]
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Lojas); ESTADO['porta'] = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    urllib.request.urlopen = urlopen_falso
    sem = semente_de(RAIZ)
    class T:
        @staticmethod
        def sleep(s): SLEEP[0] += s
        time = staticmethod(time.time)
    c.time = T
    try:
        for fn in CENARIOS:
            if escolhidos and fn.__name__ not in escolhidos: continue
            print('\n%s: %s' % (fn.__name__, fn.__doc__)); amb = Ambiente(sem)
            try: fn(amb)
            except Exception as e:
                import traceback; traceback.print_exc(); chk('%s sem exceção' % fn.__name__, False, repr(e))
            finally: amb.limpar()
    finally:
        urllib.request.urlopen = REAL_URLOPEN; srv.shutdown(); shutil.rmtree(sem, ignore_errors=True)
    falhas = [r for r in RES if not r[1]]
    print('\n==== %d verificações, %d falharam ====' % (len(RES), len(falhas)))
    for n, _, d in falhas: print('  FALHA:', n, '|', str(d)[:200])
    return 1 if falhas else 0


if __name__ == '__main__':
    sys.exit(main())

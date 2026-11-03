#!/usr/bin/env python3 -I
"""Posts de crescimento (visita ao site, salvar, enviar, comentar): cards 1080x1350 SEM preço + registro em posts.json.

É uma rotina ADICIONAL: não mexe em posts de produtos, nem no calendário existente. O conteúdo fica em
dados/crescimento.json (uma lista de posts) e este script só renderiza os cards e registra o que ainda não existe.

Cada post em dados/crescimento.json:
  id, data (AAAA-MM-DD), hora (HH:MM), tema, objetivo (visita|salvar|enviar|comentar), slides, legenda, status (padrão "agendado")
  slides: lista de {"tipo": "capa"|"lista"|"pergunta"|"final", ...}
    capa:     titulo, sub
    lista:    kicker (etiqueta curta), titulo, itens [texto, ...]
    pergunta: kicker, titulo, opcoes [texto, ...], chamada
    final:    titulo, botao, nota
  Marcadores aceitos nos textos: {ofertas} ("mais de 180"), {n_cat}, {n_lojas}, {lojas}, {data_conf}.

Regras (o script recusa o post se violar): nada de preço ("R$"), legenda com "Publicidade: links de afiliado",
até 2200 caracteres, até 8 hashtags, sem pedido de curtida/compartilhamento em troca de algo ("curta se", "marque 3"...).

Uso: FONTES=/tmp/f python3 -I tools/crescimento.py [--refazer]     (gera pastas postagens/<id>/ e registra em posts.json)
"""
import datetime, importlib.util, json, os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def garantir_fontes():
    """cards.py usa TTF em FONTES (padrão /tmp/f). Se faltar, converte os .woff2 do site (fonts/) com fontTools+brotli."""
    pasta = os.environ.get('FONTES', '/tmp/f'); os.environ['FONTES'] = pasta
    nomes = ['baloo-2-latin-700-normal', 'nunito-latin-700-normal', 'nunito-latin-800-normal']
    if all(os.path.exists(os.path.join(pasta, n + '.ttf')) for n in nomes): return
    os.makedirs(pasta, exist_ok=True)
    from fontTools.ttLib import TTFont   # pip install fonttools brotli
    for n in nomes:
        f = TTFont(os.path.join(RAIZ, 'fonts', n + '.woff2')); f.flavor = None; f.save(os.path.join(pasta, n + '.ttf'))


garantir_fontes()
spec = importlib.util.spec_from_file_location('cards', os.path.join(RAIZ, 'tools', 'cards.py'))
C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
FONTE = os.path.join(RAIZ, 'dados', 'crescimento.json')
POSTS = os.path.join(RAIZ, 'dados', 'posts.json')
ITENS = os.path.join(RAIZ, 'dados', 'itens.json')
LOJAS = {'shopee': 'Shopee', 'amazon': 'Amazon', 'meli': 'Mercado Livre', 'aliexpress': 'AliExpress', 'magalu': 'Magalu'}
PROIBIDO = [r'curta se', r'curta e', r'curte se', r'marque \d', r'marca \d', r'compartilhe para (ganhar|concorrer)', r'sorteio',
            r'ganhe ', r'de gra[cç]a', r'comente (sim|eu)']
OBJETIVOS = ('visita', 'salvar', 'enviar', 'comentar')
RODAPE = 'achadinhosdobinga.com.br  •  preço sempre com data de conferência'


def contexto():
    itens = json.load(open(ITENS, encoding='utf-8'))
    hoje = datetime.date.today()
    vis = [i for i in itens if (hoje - datetime.date.fromisoformat(i['conferido'])).days <= 30]
    lojas = sorted({i['loja'] for i in vis}, key=list(LOJAS).index)
    nomes = [LOJAS[l] for l in lojas]
    ultima = max(i['conferido'] for i in vis)
    return {'ofertas': 'mais de %d' % (len(vis) // 10 * 10), 'n_cat': str(len({i['cat'] for i in vis})), 'n_lojas': str(len(lojas)),
            'lojas': ', '.join(nomes[:-1]) + ' e ' + nomes[-1], 'data_conf': datetime.date.fromisoformat(ultima).strftime('%d/%m/%Y')}


def preencher(t, ctx):
    return re.sub(r'\{(\w+)\}', lambda m: ctx[m.group(1)] if m.group(1) in ctx else m.group(0), t)


def textos(post):
    for s in post['slides']:
        for k, v in s.items():
            if k == 'tipo': continue
            for x in (v if isinstance(v, list) else [v]):
                yield x
    yield post['legenda']


def validar(post, ctx):
    e = []
    for k in ('id', 'data', 'hora', 'tema', 'objetivo', 'slides', 'legenda'):
        if not post.get(k): e.append('falta ' + k)
    if e: return e
    if post['objetivo'] not in OBJETIVOS: e.append('objetivo inválido: ' + post['objetivo'])
    if not re.fullmatch(r'\d{4}-\d\d-\d\d', post['data']) or not re.fullmatch(r'\d\d:\d\d', post['hora']): e.append('data/hora fora do formato')
    sl = post['slides']
    if not 3 <= len(sl) <= 8 or sl[0].get('tipo') != 'capa' or sl[-1].get('tipo') != 'final': e.append('precisa de capa, 1+ miolo e final (3 a 8 slides)')
    leg = preencher(post['legenda'], ctx)
    if 'Publicidade: links de afiliado' not in leg: e.append('legenda sem "Publicidade: links de afiliado"')
    if len(leg) > 2200: e.append('legenda com mais de 2200 caracteres')
    if len(re.findall(r'#\w+', leg)) > 8: e.append('mais de 8 hashtags')
    for t in textos(post):
        t = preencher(t, ctx)
        if 'R$' in t or re.search(r'\d+\s*(reais|%\s*off|de desconto)', t, re.I): e.append('texto com preço/desconto: ' + t[:40])
        if re.search(r'\{\w+\}', t): e.append('marcador não resolvido: ' + t[:40])
        for p in PROIBIDO:
            if re.search(p, t, re.I): e.append('pedido de engajamento proibido (%s): %s' % (p, t[:40]))
    return e


# ---------- cards ----------
def rodape(d):
    d.text((C.W / 2, 1318), RODAPE, font=C.NUN7(25), fill=C.ROXO2, anchor='mm')


def titulo_auto(d, txt, largura, max_linhas, tam_max, tam_min, fonte=None):
    fonte = fonte or C.BALOO
    for tam in range(tam_max, tam_min - 1, -4):
        f = fonte(tam); ls = C.quebrar(d, txt, f, largura, max_linhas)
        if len(ls) <= max_linhas and '…' not in ls[-1]: break
    return f, tam, ls


def card_capa(s, ctx):
    img, d = C.novo(); C.logo(img, d)
    f, tam, ls = titulo_auto(d, preencher(s['titulo'], ctx).upper(), 920, 5, 112, 64)
    sub = C.quebrar(d, preencher(s['sub'], ctx), C.NUN8(44), 920, 3) if s.get('sub') else []
    alt = len(ls) * int(tam * 1.12) + (16 + len(sub) * 54 if sub else 0)
    y = 170 + max(0, (1100 - 170 - alt) // 2)
    for l in ls: d.text((80, y), l, font=f, fill=C.ROXO); y += int(tam * 1.12)
    for l in sub:
        d.text((80, y + 16), l, font=C.NUN8(44), fill=C.ROXO2); y += 54
    C.pilula(d, (C.W - 60 - (C.larg(d, 'DESLIZE', C.NUN8(40)) + 76), 1180), 'DESLIZE', C.NUN8(40), C.ROXO, C.AMARELO)
    rodape(d); return img


def card_lista(s, ctx):
    img, d = C.novo(); C.logo(img, d)
    kick = s.get('kicker')
    f, tam, ls = titulo_auto(d, preencher(s['titulo'], ctx), 920, 3, 92, 56)
    fi = C.NUN8(50); itens = [preencher(x, ctx) for x in s['itens']]; gap = 28
    alt = lambda fi: [max(150, int(fi.size * 1.22) * len(C.quebrar(d, t, fi, 740, 5)) + 56) for t in itens]
    topo = (112 if kick else 0) + len(ls) * int(tam * 1.12) + 36
    while topo + sum(alt(fi)) + gap * (len(itens) - 1) > 1090 and fi.size > 32: fi = C.NUN8(fi.size - 2)
    hs = alt(fi)
    y = 170 + max(0, (1110 - 170 - topo - sum(hs) - gap * (len(itens) - 1)) // 2)
    if kick:
        C.pilula(d, (80, y), preencher(kick, ctx).upper(), C.NUN8(34), C.AMARELO, C.ROXO, pad=30); y += 112
    for l in ls: d.text((80, y), l, font=f, fill=C.ROXO); y += int(tam * 1.12)
    y += 36
    for n, (t, h) in enumerate(zip(itens, hs), 1):
        d.rounded_rectangle((80, y, 1000, y + h), radius=36, fill='white')
        d.ellipse((104, y + h / 2 - 36, 176, y + h / 2 + 36), fill=C.AMARELO, outline=C.ROXO, width=5)
        d.text((140, y + h / 2 + 2), str(n), font=C.BALOO(46), fill=C.ROXO, anchor='mm')
        ls2 = C.quebrar(d, t, fi, 740, 5); lh = int(fi.size * 1.22); ty = y + (h - len(ls2) * lh) / 2
        for l in ls2: d.text((204, ty), l, font=fi, fill=C.ROXO); ty += lh
        y += h + gap
    rodape(d); return img


def card_pergunta(s, ctx):
    img, d = C.novo(); C.logo(img, d)
    y = 190
    if s.get('kicker'):
        C.pilula(d, (80, y), preencher(s['kicker'], ctx).upper(), C.NUN8(34), C.AMARELO, C.ROXO, pad=30); y += 112
    f, tam, ls = titulo_auto(d, preencher(s['titulo'], ctx), 920, 4, 96, 60)
    for l in ls: d.text((80, y), l, font=f, fill=C.ROXO); y += int(tam * 1.12)
    y += 36; fo = C.NUN8(44)
    for o in s['opcoes']:
        d.rounded_rectangle((80, y, 1000, y + 104), radius=52, fill='white', outline=C.ROXO, width=5)
        d.text((C.W / 2, y + 54), preencher(o, ctx), font=fo, fill=C.ROXO, anchor='mm'); y += 124
    if s.get('chamada'):
        C.pilula(d, (80, min(y + 20, 1190)), preencher(s['chamada'], ctx).upper(), C.NUN8(38), C.ROXO, C.AMARELO)
    rodape(d); return img


def card_final(s, ctx):
    img, d = C.novo(); C.logo(img, d)
    f, tam, ls = titulo_auto(d, preencher(s['titulo'], ctx), 920, 3, 120, 70)
    y = 440
    for l in ls: d.text((C.W / 2, y), l, font=f, fill=C.ROXO, anchor='mm'); y += int(tam * 1.14)
    fb = C.NUN8(48); b = preencher(s.get('botao', 'LINK NA BIO'), ctx).upper(); w = C.larg(d, b, fb) + 76
    C.pilula(d, ((C.W - w) / 2, y + 60), b, fb, C.ROXO, C.AMARELO)
    if s.get('nota'):
        d.text((C.W / 2, y + 220), preencher(s['nota'], ctx), font=C.NUN7(34), fill=C.ROXO2, anchor='mm')
    d.text((C.W / 2, 1180), 'Publicidade: links de afiliado', font=C.NUN8(36), fill=C.ROXO, anchor='mm')
    rodape(d); return img


CARDS = {'capa': card_capa, 'lista': card_lista, 'pergunta': card_pergunta, 'final': card_final}


def main():
    refazer = '--refazer' in sys.argv
    ctx = contexto()
    specs = json.load(open(FONTE, encoding='utf-8'))
    posts = json.load(open(POSTS, encoding='utf-8'))
    ids = {p['id'] for p in posts}
    erros, novos = [], 0
    for sp in specs:
        e = validar(sp, ctx)
        if e: erros += ['%s: %s' % (sp.get('id', '?'), x) for x in e]; continue
        pasta = os.path.join(RAIZ, 'postagens', sp['id'])
        if sp['id'] in ids and not refazer: continue
        os.makedirs(pasta, exist_ok=True)
        imgs = []
        for k, s in enumerate(sp['slides'], 1):
            caminho = 'postagens/%s/%02d.jpg' % (sp['id'], k)
            CARDS[s['tipo']](s, ctx).save(os.path.join(RAIZ, caminho), 'JPEG', quality=92); imgs.append(caminho)
        if sp['id'] in ids: continue
        posts.append({'id': sp['id'], 'data': sp['data'], 'hora': sp['hora'], 'formato': 'carrossel', 'loja': 'todas', 'tema': sp['tema'],
                      'canal': 'ig', 'produtos': [], 'sem_preco': True, 'objetivo': sp['objetivo'], 'status': sp.get('status', 'agendado'),
                      'nota': 'Post de crescimento (sem preço), criado em %s.' % datetime.date.today().strftime('%d/%m/%Y'),
                      'imagens': imgs, 'legenda': preencher(sp['legenda'], ctx)})
        novos += 1; print('criado:', sp['id'], sp['data'], sp['hora'], len(imgs), 'cards')
    if erros:
        print('ERROS:'); [print(' -', x) for x in erros]; return 1
    if novos:
        with open(POSTS, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(posts, ensure_ascii=False, indent=1) + '\n')
    print('crescimento: %d post(s) novo(s)' % novos)
    return 0


if __name__ == '__main__':
    sys.exit(main())

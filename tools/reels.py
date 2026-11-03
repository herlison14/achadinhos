#!/usr/bin/env python3 -I
"""Reel "Caiu de preço" (vertical 1080x1920, 30 fps, ~17 s, COM trilha e efeitos) feito só com dados reais de dados/quedas.json + itens.json.

Regras: só entra item cuja queda está no histórico (antes -> agora, com datas), cujo preço atual (itens.json) é o preço "agora",
conferido há no máximo 7 dias e com foto local. Nada de desconto inventado: o percentual vem das duas conferências.
Visual: fundo escuro animado, foto em painel com sombra, nome, preço antigo riscado, preço novo com "pop", selo "-X%" com tremida,
confete no final. Áudio: batida e efeitos sintetizados em tools/reel_audio.py (originais, livres de direitos autorais).
Saída: postagens/<id>/reel.mp4 (+ capa.jpg) e a legenda em dados/posts.json como post "planejado" (formato "reel").
O robô ainda NÃO publica Reels: o post só entra na fila depois de revisado.

Uso: python3 -I tools/reels.py [--max 4] [--id AAAA-MM-DD-queda-do-dia] [--sem-registrar] [--amostra PASTA]
  --amostra PASTA: só grava alguns quadros PNG (para conferir o visual) e não gera vídeo nem registra.
Precisa de ffmpeg, numpy e Pillow; fontes convertidas sozinhas de fonts/*.woff2 (fonttools+brotli).
"""
import argparse, datetime, html, importlib.util, json, math, os, random, subprocess, sys, tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))
spec = importlib.util.spec_from_file_location('cresc', os.path.join(RAIZ, 'tools', 'crescimento.py'))
CR = importlib.util.module_from_spec(spec); spec.loader.exec_module(CR)
C = CR.C
getattr(CR, 'garantir_fontes', lambda: None)()
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import reel_audio

W, H, FPS = 1080, 1920, 30
BPM = 120
T_INTRO, T_ITEM, T_FIM = 2.0, 3.0, 3.0          # múltiplos de 0,5 s: cada cena entra no tempo da batida
BRANCO, LAV, ESCURO = '#FFFFFF', '#D9CCFF', '#1B0A40'
LOJAS = C.LOJAS


# ---------- utilidades de dados ----------
def br(v):
    return 'R$ ' + v


def pct(antes, agora):
    a = float(antes.replace('.', '').replace(',', '.')); b = float(agora.replace('.', '').replace(',', '.'))
    return int(round((a - b) / a * 100))


# ---------- utilidades de animação ----------
def lim(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, ini, dur):
    return lim((t - ini) / dur)


def out_cubic(x):
    return 1 - (1 - x) ** 3


def out_back(x, s=1.9):
    x = lim(x); c = s + 1
    return 1 + c * (x - 1) ** 3 + s * (x - 1) ** 2


def tremida(t, ini, dur=0.45, amp=14):
    """deslocamento (dx, dy) que decai depois de um impacto em 'ini'."""
    if not (ini <= t < ini + dur): return 0, 0
    k = (1 - (t - ini) / dur) ** 2; a = (t - ini) * 70
    return int(math.sin(a) * amp * k), int(math.cos(a * 1.3) * amp * k * 0.6)


def flash(img, a):
    return Image.blend(img, Image.new('RGB', img.size, 'white'), lim(a, 0, 0.85)) if a > 0.01 else img


# ---------- camadas (cache) ----------
_cache = {}


def fonte_larg(f, txt):
    return ImageDraw.Draw(Image.new('L', (1, 1))).textlength(txt, font=f)


def txt(texto, f, cor, sombra=None, desl=6):
    k = ('t', texto, (getattr(f, 'path', None), getattr(f, 'size', 0)), cor, sombra)
    if k in _cache: return _cache[k]
    w = int(fonte_larg(f, texto)) + 60; h = int(f.size * 1.6)
    lay = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    if sombra: d.text((w / 2 + desl, h / 2 + desl), texto, font=f, fill=sombra, anchor='mm')
    d.text((w / 2, h / 2), texto, font=f, fill=cor, anchor='mm')
    _cache[k] = lay; return lay


def pilula_lay(texto, f, bg, fg, pad=46, alt=None):
    k = ('p', texto, (getattr(f, 'path', None), getattr(f, 'size', 0)), bg, fg)
    if k in _cache: return _cache[k]
    w = int(fonte_larg(f, texto)) + 2 * pad; h = alt or int(f.size * 1.75)
    lay = Image.new('RGBA', (w + 20, h + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((10, 14, 10 + w, 14 + h), radius=h // 2, fill=(0, 0, 0, 110))
    d.rounded_rectangle((10, 10, 10 + w, 10 + h), radius=h // 2, fill=bg)
    d.text((10 + w / 2, 10 + h / 2 + 2), texto, font=f, fill=fg, anchor='mm')
    _cache[k] = lay; return lay


def colar(img, lay, cx, cy, esc=1.0, rot=0, alp=1.0):
    if esc <= 0.01 or alp <= 0.01: return
    if abs(esc - 1) > 0.002: lay = lay.resize((max(1, int(lay.width * esc)), max(1, int(lay.height * esc))), Image.BILINEAR)
    if rot: lay = lay.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alp < 0.99:
        lay = lay.copy(); lay.putalpha(lay.getchannel('A').point(lambda v: int(v * alp)))
    img.paste(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)), lay)


def fundo_base():
    if 'fundo' in _cache: return _cache['fundo']
    y = np.linspace(0, 1, H)[:, None, None]
    a = np.array([0x1B, 0x0A, 0x40], float); b = np.array([0x45, 0x1E, 0x8C], float)
    arr = (a * (1 - y) + b * y) * np.ones((1, W, 1))
    img = Image.fromarray(arr.astype('uint8'), 'RGB'); _cache['fundo'] = img
    glow = Image.new('RGBA', (900, 900), (0, 0, 0, 0)); d = ImageDraw.Draw(glow)
    d.ellipse((100, 100, 800, 800), fill=(138, 80, 255, 120))
    _cache['glow'] = glow.filter(ImageFilter.GaussianBlur(120))
    return img


def fundo(t):
    img = fundo_base().copy(); g = _cache['glow']
    img.paste(g, (int(-200 + 140 * math.sin(t * 0.7)), int(80 + 90 * math.cos(t * 0.5))), g)
    img.paste(g, (int(500 + 120 * math.cos(t * 0.6)), int(1000 + 110 * math.sin(t * 0.8))), g)
    return img


def logo(img, t=0.0, alp=1.0):
    k = 'logo'
    if k not in _cache:
        lay = Image.new('RGBA', (460, 110), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        m = Image.open(os.path.join(RAIZ, 'img', 'marca.webp')).convert('RGB').resize((86, 86), Image.LANCZOS)
        mask = Image.new('L', (86, 86), 0); ImageDraw.Draw(mask).ellipse((0, 0, 85, 85), fill=255)
        lay.paste(m, (8, 12), mask)
        d.text((112, 14), 'achadinhos', font=C.BALOO(44), fill=BRANCO)
        d.text((112, 56), 'do binga', font=C.BALOO(44), fill=C.AMARELO)
        _cache[k] = lay
    colar(img, _cache[k], 70 + 230, 170, alp=alp)


def painel(i):
    k = ('painel', i['id'])
    if k in _cache: return _cache[k]
    lado = 700
    fr = C.arred(C.encaixar(C.foto(i['id']), lado, 36), 60)
    lay = Image.new('RGBA', (lado + 140, lado + 140), (0, 0, 0, 0))
    sombra = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(sombra).rounded_rectangle((70, 90, 70 + lado, 90 + lado), radius=60, fill=(0, 0, 0, 150))
    lay.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(26)))
    lay.alpha_composite(fr, (70, 70))
    _cache[k] = lay; return lay


def etiqueta_loja(loja):
    nome, bg, fg = LOJAS.get(loja, (loja.title(), '#EEEEEE', '#222222'))
    return pilula_lay(nome, C.NUN8(40), bg, fg, pad=34, alt=66)


# ---------- cenas ----------
def cena_intro(n, data, t):
    img = fundo(t); logo(img, t)
    p = out_cubic(prog(t, 0.05, 0.4))
    colar(img, txt('CAIU DE', C.BALOO(180), BRANCO), 540 - 700 * (1 - p), 640, alp=0.3 + 0.7 * p)
    dx, dy = tremida(t, 0.5)
    e = out_back(prog(t, 0.5, 0.45))
    colar(img, txt('PREÇO', C.BALOO(330), C.AMARELO, sombra=C.VERM, desl=12), 540, 900, esc=0.3 + 0.7 * e, alp=prog(t, 0.5, 0.12))
    w = 700 * out_cubic(prog(t, 0.95, 0.35))
    if w > 2:
        d = ImageDraw.Draw(img); d.rounded_rectangle((540 - w / 2, 1100, 540 + w / 2, 1118), radius=9, fill=C.VERM)
    colar(img, txt('%d achadinhos que baixaram' % n, C.NUN8(58), BRANCO), 540, 1230 + 30 * (1 - prog(t, 1.1, 0.3)), alp=prog(t, 1.1, 0.3))
    colar(img, txt('preços conferidos até %s' % data, C.NUN7(42), LAV), 540, 1310 + 30 * (1 - prog(t, 1.3, 0.3)), alp=prog(t, 1.3, 0.3))
    img = ImageChops.offset(img, dx, dy) if (dx or dy) else img
    return flash(img, 0.5 * (1 - prog(t, 0, 0.12)))


def cena_item(i, q, k, n, u):
    """u = segundos desde o começo da cena (0 a 3)."""
    img = fundo(u + 5 * k); logo(img, u)
    colar(img, etiqueta_loja(i['loja']), 880, 170, esc=out_back(prog(u, 0.05, 0.3)))
    e = out_back(prog(u, 0.0, 0.5), 1.6); resp = 1 + 0.012 * math.sin(u * 2 * math.pi * 2)
    colar(img, painel(i), 540, 590 + 40 * (1 - out_cubic(prog(u, 0, 0.35))), esc=(0.55 + 0.45 * e) * resp, alp=prog(u, 0, 0.15))
    # indicador k/n
    ci = Image.new('RGBA', (150, 150), (0, 0, 0, 0)); d = ImageDraw.Draw(ci)
    d.ellipse((8, 8, 142, 142), fill=C.AMARELO, outline=C.ROXO, width=7); d.text((75, 78), '%d/%d' % (k, n), font=C.BALOO(54), fill=C.ROXO, anchor='mm')
    colar(img, ci, 225, 305, esc=0.8 * out_back(prog(u, 0.2, 0.35)), rot=-8)
    # nome
    a = prog(u, 0.4, 0.4); nome = html.unescape(i['nome']); f = C.NUN8(52)
    linhas = C.quebrar(ImageDraw.Draw(Image.new('L', (1, 1))), nome, f, 900, 2)
    for r, l in enumerate(linhas):
        colar(img, txt(l, f, BRANCO), 540, 1010 + r * 62 + 36 * (1 - out_cubic(a)), alp=a)
    # preço antigo + risco
    base_y = 1010 + len(linhas) * 62 + 60
    ao = prog(u, 0.9, 0.3); tx_antes = 'de ' + br(q['antes'])
    colar(img, txt(tx_antes, C.NUN7(50), LAV), 540, base_y, alp=ao)
    w = fonte_larg(C.NUN7(50), tx_antes) * out_cubic(prog(u, 1.0, 0.35))
    if w > 2:
        d = ImageDraw.Draw(img); d.line((540 - fonte_larg(C.NUN7(50), tx_antes) / 2, base_y + 4, 540 - fonte_larg(C.NUN7(50), tx_antes) / 2 + w, base_y + 4), fill=C.VERM, width=8)
    # preço novo
    y_novo = base_y + 130; pn = prog(u, 1.5, 0.5)
    colar(img, txt('por ' + br(q['agora']), C.BALOO(150), C.AMARELO, sombra=ESCURO, desl=8), 500, y_novo, esc=1 + 0.5 * (1 - out_back(pn)) if pn < 1 else 1.0, alp=prog(u, 1.5, 0.1))
    # selo
    p = pct(q['antes'], q['agora']); dx, dy = tremida(u, 2.0)
    es = out_back(prog(u, 2.0, 0.4), 2.4)
    selo = Image.new('RGBA', (300, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(selo)
    d.ellipse((20, 26, 280, 286), fill=(0, 0, 0, 110)); d.ellipse((14, 14, 274, 274), fill=C.VERM, outline=BRANCO, width=9)
    d.text((144, 82), 'CAIU', font=C.NUN8(40), fill=BRANCO, anchor='mm'); d.text((144, 164), '-%d%%' % p, font=C.BALOO(112), fill=BRANCO, anchor='mm')
    d.text((144, 232), 'no preço', font=C.NUN7(34), fill=BRANCO, anchor='mm')
    colar(img, selo, 845, 845, esc=(0.4 + 0.6 * es) * 0.8, rot=-11, alp=prog(u, 2.0, 0.1))
    colar(img, txt('conferido em %s (antes: %s)' % (datetime.date.fromisoformat(i['conferido']).strftime('%d/%m/%Y'),
          datetime.date.fromisoformat(q['data_antes']).strftime('%d/%m') if q.get('data_antes') else 'conferência anterior'), C.NUN7(34), LAV), 540, y_novo + 110, alp=prog(u, 2.3, 0.3))
    colar(img, txt('Publicidade: links de afiliado • o preço pode mudar', C.NUN7(28), '#A99BD6'), 540, 1490, alp=0.9)
    if (dx or dy): img = ImageChops.offset(img, dx, dy)
    img = flash(img, 0.55 * (1 - prog(u, 0, 0.12)) + 0.3 * (1 - prog(u, 1.5, 0.15)) * (1 if u >= 1.5 else 0))
    return img


def confete(n=70):
    rnd = random.Random(11); cores = [C.AMARELO, C.VERM, '#FFFFFF', '#8A50FF', '#46D2A0']
    return [(rnd.randint(40, 1040), rnd.uniform(-900, -50), rnd.uniform(-60, 60), rnd.uniform(500, 900), rnd.uniform(0, 6.3), rnd.uniform(-9, 9),
             rnd.choice(cores), rnd.randint(14, 30)) for _ in range(n)]


CONFETE = confete()


def cena_fim(u):
    img = fundo(u + 20); logo(img, u)
    colar(img, txt('Quer ver', C.BALOO(130), BRANCO), 540, 620, esc=0.4 + 0.6 * out_back(prog(u, 0.1, 0.4)), alp=prog(u, 0.1, 0.1))
    colar(img, txt('todas as ofertas?', C.BALOO(130), C.AMARELO, sombra=C.VERM, desl=7), 540, 780, esc=0.4 + 0.6 * out_back(prog(u, 0.4, 0.4)), alp=prog(u, 0.4, 0.1))
    pulso = 1 + 0.045 * math.sin(u * 2 * math.pi * 2) if u > 1.0 else 1
    colar(img, pilula_lay('LINK NA BIO', C.NUN8(66), C.AMARELO, C.ROXO, pad=70), 540, 1040, esc=(0.3 + 0.7 * out_back(prog(u, 0.9, 0.45))) * pulso, alp=prog(u, 0.9, 0.1))
    colar(img, txt('achadinhosdobinga.com.br', C.NUN8(48), BRANCO), 540, 1230, alp=prog(u, 1.3, 0.3))
    colar(img, txt('Salva e manda pra quem compra online', C.NUN7(40), LAV), 540, 1310, alp=prog(u, 1.5, 0.3))
    colar(img, txt('Publicidade: links de afiliado', C.NUN8(30), '#A99BD6'), 540, 1490)
    d = ImageDraw.Draw(img)
    for x, y0, vx, vy, ang, rot, cor, s in CONFETE:
        if u < 0.35: break
        tt = u - 0.35; y = y0 + vy * tt + 300 * tt * tt; xx = x + vx * tt + 25 * math.sin(tt * 4 + ang)
        if -40 < y < H + 40:
            c = math.cos(ang + rot * tt); d.polygon([(xx - s * abs(c) / 2, y - s / 2), (xx + s * abs(c) / 2, y - s / 2), (xx + s * abs(c) / 2, y + s / 2), (xx - s * abs(c) / 2, y + s / 2)], fill=cor)
    return flash(img, 0.5 * (1 - prog(u, 0, 0.12)))


# ---------- linha do tempo ----------
def quadro(t, esc, n, data):
    if t < T_INTRO: return cena_intro(n, data, t)
    t2 = t - T_INTRO
    if t2 < n * T_ITEM:
        k = int(t2 // T_ITEM); i, q = esc[k]; return cena_item(i, q, k + 1, n, t2 - k * T_ITEM)
    return cena_fim(t2 - n * T_ITEM)


def sfx_lista(n):
    s = [(0.0, 'whoosh'), (0.5, 'pop'), (1.0, 'pop')]
    for k in range(n):
        b = T_INTRO + k * T_ITEM
        s += [(b - 0.05, 'whoosh'), (b + 0.4, 'pop'), (b + 1.5, 'cha'), (b + 2.0, 'pop')]
    b = T_INTRO + n * T_ITEM
    s += [(b - 0.05, 'whoosh'), (b + 0.1, 'pop'), (b + 0.4, 'pop'), (b + 0.9, 'pop'), (b + 0.35, 'brilho')]
    return s


def gerar_video(esc, n, data, saida):
    total = T_INTRO + n * T_ITEM + T_FIM
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, 'trilha.wav'); reel_audio.salvar(wav, reel_audio.sintetizar(total, BPM, sfx_lista(n)))
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-',
               '-i', wav, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', str(FPS),
               '-af', 'alimiter=limit=0.7:level=0', '-c:a', 'aac', '-b:a', '160k', '-t', '%.2f' % total, '-movflags', '+faststart', saida]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for f in range(int(total * FPS)):
            p.stdin.write(quadro(f / FPS, esc, n, data).tobytes())
        p.stdin.close()
        if p.wait(): raise SystemExit('ffmpeg falhou')
    return total


def escolher(maximo):
    itens = {i['id']: i for i in json.load(open(os.path.join(RAIZ, 'dados', 'itens.json'), encoding='utf-8'))}
    quedas = json.load(open(os.path.join(RAIZ, 'dados', 'quedas.json'), encoding='utf-8'))
    hist = json.load(open(os.path.join(RAIZ, 'dados', 'historico.json'), encoding='utf-8'))
    hoje = datetime.date.today(); out = []
    for q in sorted(quedas, key=lambda q: -q['pct']):
        i = itens.get(q['id'])
        if not i or i['preco'] != q['agora']: continue
        if (hoje - datetime.date.fromisoformat(i['conferido'])).days > 7: continue
        if not (os.path.exists(os.path.join(RAIZ, 'img', 'cards', i['id'] + '.jpg')) or os.path.exists(os.path.join(RAIZ, 'img', i['id'] + '.webp'))): continue
        h = hist.get(i['id']) or []
        antes = [d for d, p in h if p == q['antes']]
        q = dict(q, data_antes=antes[-1] if antes else None)
        if q['pct'] < 3: continue
        out.append((i, q))
    # no máximo 2 por loja, para variar
    por_loja, esc = {}, []
    for i, q in out:
        if por_loja.get(i['loja'], 0) >= 2: continue
        por_loja[i['loja']] = por_loja.get(i['loja'], 0) + 1; esc.append((i, q))
        if len(esc) == maximo: break
    return esc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--max', type=int, default=4)
    ap.add_argument('--id', default=datetime.date.today().isoformat() + '-queda-do-dia')
    ap.add_argument('--sem-registrar', action='store_true')
    ap.add_argument('--amostra', metavar='PASTA')
    a = ap.parse_args()
    esc = escolher(a.max)
    if len(esc) < 2: print('poucas quedas reais e atuais (%d): nada gerado' % len(esc)); return 1
    n = len(esc); data = max(datetime.date.fromisoformat(i['conferido']) for i, _ in esc).strftime('%d/%m/%Y')
    if a.amostra:
        os.makedirs(a.amostra, exist_ok=True)
        for t in (0.25, 0.7, 1.9, T_INTRO + 0.3, T_INTRO + 1.2, T_INTRO + 1.7, T_INTRO + 2.6, T_INTRO + n * T_ITEM + 0.5, T_INTRO + n * T_ITEM + 2.0):
            quadro(t, esc, n, data).save(os.path.join(a.amostra, 'q_%05.2f.png' % t))
        print('amostras em', a.amostra); return 0
    pasta = os.path.join(RAIZ, 'postagens', a.id); os.makedirs(pasta, exist_ok=True)
    quadro(1.9, esc, n, data).crop((0, 285, W, 1635)).save(os.path.join(pasta, 'capa.jpg'), 'JPEG', quality=90)
    dur = gerar_video(esc, n, data, os.path.join(pasta, 'reel.mp4'))
    linhas = []
    for k, (i, q) in enumerate(esc, 1):
        linhas.append('%d. %s: de R$ %s para R$ %s (conferido em %s)' % (k, html.unescape(i['nome']), q['antes'], q['agora'],
                      datetime.date.fromisoformat(i['conferido']).strftime('%d/%m/%Y')))
    legenda = ('Caiu de preço 📉 %d achadinhos que baixaram nas últimas conferências\n\n%s\n\n'
               'O preço pode mudar: confirme na loja antes de comprar.\nTodas as ofertas, com preço e data, no site: link na bio 🔗\n'
               'Gostou? Curte, salva e manda pra quem compra online.\n\nPublicidade: links de afiliado.\n\n#caiudepreço #achadinhos #ofertas #comprasonline') % (n, '\n'.join(linhas))
    print('Reel: %s (%.1f s, %d itens)\n%s' % (os.path.join(pasta, 'reel.mp4'), dur, n, legenda))
    if not a.sem_registrar:
        pf = os.path.join(RAIZ, 'dados', 'posts.json'); posts = json.load(open(pf, encoding='utf-8'))
        if not any(p['id'] == a.id for p in posts):
            posts.append({'id': a.id, 'data': datetime.date.today().isoformat(), 'hora': '12:30', 'formato': 'reel', 'loja': 'misto',
                          'tema': 'Caiu de preço: %d achadinhos' % n, 'canal': 'ig', 'produtos': [i['id'] for i, _ in esc],
                          'status': 'planejado', 'video': 'postagens/%s/reel.mp4' % a.id, 'objetivo': 'descoberta',
                          'nota': 'Reel gerado de dados reais (quedas.json); revisar antes de agendar.', 'legenda': legenda})
            with open(pf, 'w', encoding='utf-8', newline='\n') as f: f.write(json.dumps(posts, ensure_ascii=False, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())

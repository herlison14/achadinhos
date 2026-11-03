#!/usr/bin/env python3 -I
"""Reels temáticos SEM preço (11.11, Black Friday, dicas de compra, uso do site), na mesma linguagem visual do "Caiu de preço".

Fonte: dados/reels.json (lista). Cada item:
  id, data (AAAA-MM-DD), hora (HH:MM), objetivo, kicker, titulo (lista de linhas; a 2ª em amarelo), sub,
  pontos [{titulo, texto}] (2 a 4), fecho (frase do final), legenda (sem "R$"; com "Publicidade: links de afiliado").
Gera postagens/<id>/reel.mp4 (+ capa.jpg) e registra em dados/posts.json (formato reel, sem_preco, status agendado).
Só fatos verdadeiros e dicas gerais de compra: nada de preço, desconto, sorteio ou isca de engajamento ("curta se", "marque").

Uso: python3 -I tools/reels_tema.py [--so ID] [--refazer] [--amostra PASTA]
  --refazer: só regera vídeo e capa (não mexe na fila). --amostra: grava PNGs de conferência (sem vídeo, sem fila).
"""
import argparse, importlib.util, json, math, os, re, subprocess, sys, tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))
spec = importlib.util.spec_from_file_location('reels', os.path.join(RAIZ, 'tools', 'reels.py'))
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
C, reel_audio = R.C, R.reel_audio
from PIL import Image, ImageDraw, ImageChops

T_TIT, T_PONTO, T_FIM = 3.0, 3.5, 3.0
BRANCO, LAV = R.BRANCO, R.LAV
PROIBIDO = [r'R\$', r'\d\s?%', r'curta se', r'marque \d', r'sorteio', r'ganhe', r'de graça', r'grátis', r'desconto', r'imperdível', r'últimas unidades']


def validar(r):
    e = []
    for k in ('id', 'data', 'hora', 'kicker', 'titulo', 'pontos', 'fecho', 'legenda'):
        if not r.get(k): e.append('falta ' + k)
    if e: return e
    if not 2 <= len(r['pontos']) <= 4: e.append('2 a 4 pontos')
    if len(r['titulo']) != 2: e.append('título com 2 linhas')
    if 'Publicidade' not in r['legenda']: e.append('legenda sem "Publicidade"')
    if len(r['legenda']) > 2200 or len(re.findall(r'#\w+', r['legenda'])) > 8: e.append('legenda longa ou com mais de 8 hashtags')
    tudo = json.dumps(r, ensure_ascii=False)
    for pad in PROIBIDO:
        if re.search(pad, tudo, re.I): e.append('texto proibido: ' + pad)
    return e


def ajustar(texto, base, maxw=940):
    """fonte BALOO no maior tamanho (até 'base') em que o texto cabe na largura útil do Reel."""
    tam = base
    while tam > 70 and R.fonte_larg(C.BALOO(tam), texto) > maxw: tam -= 6
    return C.BALOO(tam)


# ---------- cenas ----------
def cena_titulo(r, t):
    img = R.fundo(t); R.logo(img, t)
    p = R.out_back(R.prog(t, 0.05, 0.4))
    R.colar(img, R.pilula_lay(r['kicker'], C.NUN8(46), C.VERM, BRANCO, pad=44), 540, 480, esc=0.4 + 0.6 * p, alp=R.prog(t, 0.05, 0.1))
    dx, dy = R.tremida(t, 0.5)
    R.colar(img, R.txt(r['titulo'][0], ajustar(r['titulo'][0], 150), BRANCO), 540 - 700 * (1 - R.out_cubic(R.prog(t, 0.3, 0.4))), 720, alp=0.3 + 0.7 * R.prog(t, 0.3, 0.2))
    R.colar(img, R.txt(r['titulo'][1], ajustar(r['titulo'][1], 190), C.AMARELO, sombra=C.VERM, desl=10), 540, 930,
            esc=0.3 + 0.7 * R.out_back(R.prog(t, 0.5, 0.45)), alp=R.prog(t, 0.5, 0.12))
    w = 640 * R.out_cubic(R.prog(t, 1.0, 0.35))
    if w > 2: ImageDraw.Draw(img).rounded_rectangle((540 - w / 2, 1090, 540 + w / 2, 1106), radius=8, fill=C.VERM)
    if r.get('sub'):
        a = R.prog(t, 1.3, 0.35)
        R.colar(img, R.txt(r['sub'], C.NUN8(54), BRANCO), 540, 1210 + 30 * (1 - a), alp=a)
    if dx or dy: img = ImageChops.offset(img, dx, dy)
    return R.flash(img, 0.5 * (1 - R.prog(t, 0, 0.12)))


def cena_ponto(r, k, n, u):
    pt = r['pontos'][k - 1]
    img = R.fundo(u + 7 * k); R.logo(img, u)
    R.colar(img, R.pilula_lay('%d de %d' % (k, n), C.NUN8(38), C.AMARELO, C.ROXO, pad=36, alt=64), 880, 170, esc=R.out_back(R.prog(u, 0.05, 0.3)))
    dx, dy = R.tremida(u, 0.3, 0.4, 10)
    ci = Image.new('RGBA', (360, 360), (0, 0, 0, 0)); d = ImageDraw.Draw(ci)
    d.ellipse((30, 40, 330, 340), fill=(0, 0, 0, 110)); d.ellipse((20, 20, 320, 320), fill=C.AMARELO, outline=BRANCO, width=10)
    d.text((170, 178), str(k), font=C.BALOO(220), fill=C.ROXO, anchor='mm')
    R.colar(img, ci, 540, 560, esc=(0.3 + 0.7 * R.out_back(R.prog(u, 0.0, 0.5), 2.2)) * (1 + 0.015 * math.sin(u * 4 * math.pi)), alp=R.prog(u, 0, 0.1))
    a = R.prog(u, 0.45, 0.4)
    f = C.BALOO(108); linhas = C.quebrar(ImageDraw.Draw(Image.new('L', (1, 1))), pt['titulo'], f, 900, 2)
    for i, l in enumerate(linhas):
        R.colar(img, R.txt(l, f, C.AMARELO, sombra=R.ESCURO, desl=6), 540, 900 + i * 118 + 40 * (1 - R.out_cubic(a)), alp=a)
    y = 900 + len(linhas) * 118 + 70
    ft = C.NUN8(54); ls = C.quebrar(ImageDraw.Draw(Image.new('L', (1, 1))), pt['texto'], ft, 880, 4)
    b = R.prog(u, 0.9, 0.4)
    for i, l in enumerate(ls):
        R.colar(img, R.txt(l, ft, BRANCO), 540, y + i * 68 + 30 * (1 - R.out_cubic(b)), alp=b)
    R.colar(img, R.txt('Publicidade: links de afiliado', C.NUN7(28), '#A99BD6'), 540, 1490, alp=0.9)
    if dx or dy: img = ImageChops.offset(img, dx, dy)
    return R.flash(img, 0.55 * (1 - R.prog(u, 0, 0.12)))


def cena_fim(r, u):
    img = R.fundo(u + 20); R.logo(img, u)
    linhas = r['fecho'].split('|')
    for i, l in enumerate(linhas[:2]):
        R.colar(img, R.txt(l, C.BALOO(118), BRANCO if i == 0 else C.AMARELO, sombra=C.VERM if i else None, desl=7), 540, 600 + i * 150,
                esc=0.4 + 0.6 * R.out_back(R.prog(u, 0.1 + 0.25 * i, 0.4)), alp=R.prog(u, 0.1 + 0.25 * i, 0.1))
    pulso = 1 + 0.045 * math.sin(u * 2 * math.pi * 2) if u > 1.0 else 1
    R.colar(img, R.pilula_lay('LINK NA BIO', C.NUN8(66), C.AMARELO, C.ROXO, pad=70), 540, 1000,
            esc=(0.3 + 0.7 * R.out_back(R.prog(u, 0.9, 0.45))) * pulso, alp=R.prog(u, 0.9, 0.1))
    R.colar(img, R.txt('Curte, salva e manda pra quem vai comprar', C.NUN8(44), BRANCO), 540, 1180, alp=R.prog(u, 1.3, 0.3))
    R.colar(img, R.txt('achadinhosdobinga.com.br', C.NUN7(42), LAV), 540, 1255, alp=R.prog(u, 1.5, 0.3))
    R.colar(img, R.txt('Publicidade: links de afiliado', C.NUN8(30), '#A99BD6'), 540, 1490)
    d = ImageDraw.Draw(img)
    for x, y0, vx, vy, ang, rot, cor, s in R.CONFETE:
        if u < 0.35: break
        tt = u - 0.35; y = y0 + vy * tt + 300 * tt * tt; xx = x + vx * tt + 25 * math.sin(tt * 4 + ang)
        if -40 < y < R.H + 40:
            c = abs(math.cos(ang + rot * tt)); d.rectangle((xx - s * c / 2, y - s / 2, xx + s * c / 2, y + s / 2), fill=cor)
    return R.flash(img, 0.5 * (1 - R.prog(u, 0, 0.12)))


def quadro(r, t):
    n = len(r['pontos'])
    if t < T_TIT: return cena_titulo(r, t)
    t2 = t - T_TIT
    if t2 < n * T_PONTO:
        k = int(t2 // T_PONTO); return cena_ponto(r, k + 1, n, t2 - k * T_PONTO)
    return cena_fim(r, t2 - n * T_PONTO)


def sfx(n):
    s = [(0.0, 'whoosh'), (0.5, 'pop'), (1.0, 'pop')]
    for k in range(n):
        b = T_TIT + k * T_PONTO
        s += [(b - 0.05, 'whoosh'), (b + 0.3, 'pop'), (b + 0.5, 'pop'), (b + 1.0, 'pop')]
    b = T_TIT + n * T_PONTO
    s += [(b - 0.05, 'whoosh'), (b + 0.1, 'pop'), (b + 0.35, 'pop'), (b + 0.9, 'brilho')]
    return s


def video(r, saida):
    n = len(r['pontos']); total = T_TIT + n * T_PONTO + T_FIM
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, 'trilha.wav'); reel_audio.salvar(wav, reel_audio.sintetizar(total, R.BPM, sfx(n)))
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (R.W, R.H), '-r', str(R.FPS), '-i', '-',
               '-i', wav, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', str(R.FPS),
               '-af', 'alimiter=limit=0.7:level=0', '-c:a', 'aac', '-b:a', '160k', '-t', '%.2f' % total, '-movflags', '+faststart', saida]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for f in range(int(total * R.FPS)): p.stdin.write(quadro(r, f / R.FPS).tobytes())
        p.stdin.close()
        if p.wait(): raise SystemExit('ffmpeg falhou')
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--so'); ap.add_argument('--refazer', action='store_true'); ap.add_argument('--amostra')
    a = ap.parse_args()
    lista = json.load(open(os.path.join(RAIZ, 'dados', 'reels.json'), encoding='utf-8'))
    pf = os.path.join(RAIZ, 'dados', 'posts.json'); posts = json.load(open(pf, encoding='utf-8')); ids = {p['id'] for p in posts}
    ruim = 0
    for r in lista:
        if a.so and r['id'] != a.so: continue
        e = validar(r)
        if e: print('REPROVADO', r.get('id'), '; '.join(e)); ruim += 1; continue
        n = len(r['pontos']); pasta = os.path.join(RAIZ, 'postagens', r['id'])
        if a.amostra:
            os.makedirs(a.amostra, exist_ok=True)
            for t in (1.9, T_TIT + 0.3, T_TIT + 1.6, T_TIT + n * T_PONTO + 1.8):
                quadro(r, t).save(os.path.join(a.amostra, '%s_%05.2f.png' % (r['id'][-18:], t)))
            continue
        if r['id'] in ids and not a.refazer: continue
        os.makedirs(pasta, exist_ok=True)
        quadro(r, 1.9).crop((0, 285, R.W, 1635)).save(os.path.join(pasta, 'capa.jpg'), 'JPEG', quality=90)
        dur = video(r, os.path.join(pasta, 'reel.mp4')); print('OK', r['id'], '%.1f s' % dur)
        if r['id'] not in ids:
            posts.append({'id': r['id'], 'data': r['data'], 'hora': r['hora'], 'formato': 'reel', 'loja': 'todas', 'tema': r.get('tema') or ' '.join(r['titulo']),
                          'canal': 'ig', 'produtos': [], 'sem_preco': True, 'objetivo': r.get('objetivo', 'compartilhar'), 'status': 'agendado',
                          'video': 'postagens/%s/reel.mp4' % r['id'], 'legenda': r['legenda']})
    if ruim: return 1
    if not a.amostra and not a.refazer:
        with open(pf, 'w', encoding='utf-8', newline='\n') as f: f.write(json.dumps(posts, ensure_ascii=False, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())

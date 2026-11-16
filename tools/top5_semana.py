#!/usr/bin/env python3 -I
"""Reel "TOP 5 DA SEMANA" (vertical 1080x1920, 30 fps, COM trilha e efeitos) — protótipo animado no mesmo
motor de motion graphics do reels.py ("Caiu de preço"), só com moldura de contagem regressiva: mostra a
5ª maior queda real primeiro e fecha na 1ª (maior queda da semana), com selo "Nº 5" → "Nº 1" em vez do
indicador genérico "k/n". Dados 100% reais de dados/quedas.json + itens.json (mesmas regras do reels.py:
só item com queda no histórico, preço atual = "agora", conferido há no máximo 7 dias, com foto local).

Saída: postagens/<id>/reel.mp4 (+ capa.jpg) e a legenda em dados/posts.json como post "planejado"
(formato "reel"); revisar antes de agendar, igual ao reels.py.

Uso: python3 -I tools/top5_semana.py [--max 5] [--id AAAA-MM-DD-top5-da-semana] [--sem-registrar] [--amostra PASTA]
"""
import argparse, datetime, html, importlib.util, json, math, os, sys, tempfile, subprocess

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))
spec = importlib.util.spec_from_file_location('reels_base', os.path.join(RAIZ, 'tools', 'reels.py'))
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
from PIL import Image, ImageDraw, ImageChops
import reel_audio

W, H, FPS, BPM = R.W, R.H, R.FPS, R.BPM
T_INTRO, T_ITEM, T_FIM = R.T_INTRO, R.T_ITEM, R.T_FIM
BRANCO, LAV = R.BRANCO, R.LAV


# ---------- cenas (só a intro e o selo de ranking mudam; item e fim reaproveitam o reels.py) ----------
def cena_intro(n, data, t):
    img = R.fundo(t); R.logo(img, t)
    p = R.out_cubic(R.prog(t, 0.05, 0.4))
    R.colar(img, R.txt('TOP 5', R.C.BALOO(230), R.C.AMARELO, sombra=R.C.VERM, desl=12), 540, 760 - 500 * (1 - p), alp=0.3 + 0.7 * p)
    dx, dy = R.tremida(t, 0.5)
    e = R.out_back(R.prog(t, 0.5, 0.45))
    R.colar(img, R.txt('DA SEMANA', R.C.BALOO(150), BRANCO), 540, 980, esc=0.3 + 0.7 * e, alp=R.prog(t, 0.5, 0.12))
    w = 700 * R.out_cubic(R.prog(t, 0.95, 0.35))
    if w > 2:
        d = ImageDraw.Draw(img); d.rounded_rectangle((540 - w / 2, 1100, 540 + w / 2, 1118), radius=9, fill=R.C.VERM)
    R.colar(img, R.txt('%d achadinhos que mais caíram' % n, R.C.NUN8(56), BRANCO), 540, 1230 + 30 * (1 - R.prog(t, 1.1, 0.3)), alp=R.prog(t, 1.1, 0.3))
    R.colar(img, R.txt('preços conferidos até %s' % data, R.C.NUN7(42), LAV), 540, 1310 + 30 * (1 - R.prog(t, 1.3, 0.3)), alp=R.prog(t, 1.3, 0.3))
    img = ImageChops.offset(img, dx, dy) if (dx or dy) else img
    return R.flash(img, 0.5 * (1 - R.prog(t, 0, 0.12)))


def cena_item(i, q, rank, n, u):
    """Igual ao cena_item do reels.py, só troca o selo 'k/n' por 'Nº <rank>' (contagem regressiva)."""
    img = R.fundo(u + 5 * rank); R.logo(img, u)
    R.colar(img, R.etiqueta_loja(i['loja']), 880, 170, esc=R.out_back(R.prog(u, 0.05, 0.3)))
    e = R.out_back(R.prog(u, 0.0, 0.5), 1.6); resp = 1 + 0.012 * math.sin(u * 2 * math.pi * 2)
    R.colar(img, R.painel(i), 540, 590 + 40 * (1 - R.out_cubic(R.prog(u, 0, 0.35))), esc=(0.55 + 0.45 * e) * resp, alp=R.prog(u, 0, 0.15))
    # selo de ranking "Nº k" (contagem regressiva: 5 primeiro, 1 no fim)
    ci = Image.new('RGBA', (170, 170), (0, 0, 0, 0)); d = ImageDraw.Draw(ci)
    d.ellipse((8, 8, 162, 162), fill=R.C.AMARELO, outline=R.C.ROXO, width=7)
    d.text((85, 58), 'Nº', font=R.C.NUN8(34), fill=R.C.ROXO, anchor='mm')
    d.text((85, 102), str(rank), font=R.C.BALOO(70), fill=R.C.ROXO, anchor='mm')
    R.colar(img, ci, 235, 310, esc=0.8 * R.out_back(R.prog(u, 0.2, 0.35)), rot=-8)
    a = R.prog(u, 0.4, 0.4); nome = html.unescape(i['nome']); f = R.C.NUN8(52)
    linhas = R.C.quebrar(ImageDraw.Draw(Image.new('L', (1, 1))), nome, f, 900, 2)
    for r, l in enumerate(linhas):
        R.colar(img, R.txt(l, f, BRANCO), 540, 1010 + r * 62 + 36 * (1 - R.out_cubic(a)), alp=a)
    base_y = 1010 + len(linhas) * 62 + 60
    ao = R.prog(u, 0.9, 0.3); tx_antes = 'de ' + R.br(q['antes'])
    R.colar(img, R.txt(tx_antes, R.C.NUN7(50), LAV), 540, base_y, alp=ao)
    wl = R.fonte_larg(R.C.NUN7(50), tx_antes) * R.out_cubic(R.prog(u, 1.0, 0.35))
    if wl > 2:
        d = ImageDraw.Draw(img); d.line((540 - R.fonte_larg(R.C.NUN7(50), tx_antes) / 2, base_y + 4, 540 - R.fonte_larg(R.C.NUN7(50), tx_antes) / 2 + wl, base_y + 4), fill=R.C.VERM, width=8)
    y_novo = base_y + 130; pn = R.prog(u, 1.5, 0.5)
    R.colar(img, R.txt('por ' + R.br(q['agora']), R.C.BALOO(150), R.C.AMARELO, sombra=R.ESCURO, desl=8), 500, y_novo, esc=1 + 0.5 * (1 - R.out_back(pn)) if pn < 1 else 1.0, alp=R.prog(u, 1.5, 0.1))
    p = R.pct(q['antes'], q['agora']); dx, dy = R.tremida(u, 2.0)
    es = R.out_back(R.prog(u, 2.0, 0.4), 2.4)
    selo = Image.new('RGBA', (300, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(selo)
    d.ellipse((20, 26, 280, 286), fill=(0, 0, 0, 110)); d.ellipse((14, 14, 274, 274), fill=R.C.VERM, outline=BRANCO, width=9)
    d.text((144, 82), 'CAIU', font=R.C.NUN8(40), fill=BRANCO, anchor='mm'); d.text((144, 164), '-%d%%' % p, font=R.C.BALOO(112), fill=BRANCO, anchor='mm')
    d.text((144, 232), 'no preço', font=R.C.NUN7(34), fill=BRANCO, anchor='mm')
    R.colar(img, selo, 845, 845, esc=(0.4 + 0.6 * es) * 0.8, rot=-11, alp=R.prog(u, 2.0, 0.1))
    R.colar(img, R.txt('conferido em %s (antes: %s)' % (datetime.date.fromisoformat(i['conferido']).strftime('%d/%m/%Y'),
          datetime.date.fromisoformat(q['data_antes']).strftime('%d/%m') if q.get('data_antes') else 'conferência anterior'), R.C.NUN7(34), LAV), 540, y_novo + 110, alp=R.prog(u, 2.3, 0.3))
    R.colar(img, R.txt('Publicidade: links de afiliado • o preço pode mudar', R.C.NUN7(28), '#A99BD6'), 540, 1490, alp=0.9)
    if (dx or dy): img = ImageChops.offset(img, dx, dy)
    img = R.flash(img, 0.55 * (1 - R.prog(u, 0, 0.12)) + 0.3 * (1 - R.prog(u, 1.5, 0.15)) * (1 if u >= 1.5 else 0))
    return img


def quadro(t, esc, n, data):
    if t < T_INTRO: return cena_intro(n, data, t)
    t2 = t - T_INTRO
    if t2 < n * T_ITEM:
        k = int(t2 // T_ITEM); i, q = esc[k]
        rank = n - k  # contagem regressiva: 1º item mostrado = Nº n, último = Nº 1
        return cena_item(i, q, rank, n, t2 - k * T_ITEM)
    return R.cena_fim(t2 - n * T_ITEM)


def gerar_video(esc, n, data, saida):
    total = T_INTRO + n * T_ITEM + T_FIM
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, 'trilha.wav'); reel_audio.salvar(wav, reel_audio.sintetizar(total, BPM, R.sfx_lista(n)))
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-',
               '-i', wav, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', str(FPS),
               '-af', 'alimiter=limit=0.7:level=0', '-c:a', 'aac', '-b:a', '160k', '-t', '%.2f' % total, '-movflags', '+faststart', saida]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for f in range(int(total * FPS)):
            p.stdin.write(quadro(f / FPS, esc, n, data).tobytes())
        p.stdin.close()
        if p.wait(): raise SystemExit('ffmpeg falhou')
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--max', type=int, default=5)
    ap.add_argument('--id', default=datetime.date.today().isoformat() + '-top5-da-semana')
    ap.add_argument('--sem-registrar', action='store_true')
    ap.add_argument('--amostra', metavar='PASTA')
    a = ap.parse_args()
    maiores = R.escolher(a.max)  # já vem ordenado da maior queda pra menor
    if len(maiores) < 2: print('poucas quedas reais e atuais (%d): nada gerado' % len(maiores)); return 1
    esc = list(reversed(maiores))  # exibição: menor queda primeiro, maior (Nº1) por último — clímax da contagem
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
    for rank, (i, q) in enumerate(esc, 1):
        k = n - rank + 1
        linhas.append('Nº%d. %s: de R$ %s para R$ %s (conferido em %s)' % (k, html.unescape(i['nome']), q['antes'], q['agora'],
                      datetime.date.fromisoformat(i['conferido']).strftime('%d/%m/%Y')))
    linhas_ordem_post = list(reversed(linhas))  # legenda em ordem Nº1 a Nºn, mais fácil de ler
    legenda = ('Top 5 da semana 🏆 os %d achadinhos que mais caíram de preço\n\n%s\n\n'
               'O preço pode mudar: confirme na loja antes de comprar.\nTodas as ofertas, com preço e data, no site: link na bio 🔗\n'
               'Gostou? Curte, salva e manda pra quem compra online.\n\nPublicidade: links de afiliado.\n\n#top5 #achadinhos #caiudepreço #ofertas') % (n, '\n'.join(linhas_ordem_post))
    print('Reel: %s (%.1f s, %d itens)\n%s' % (os.path.join(pasta, 'reel.mp4'), dur, n, legenda))
    if not a.sem_registrar:
        pf = os.path.join(RAIZ, 'dados', 'posts.json'); posts = json.load(open(pf, encoding='utf-8'))
        if not any(p['id'] == a.id for p in posts):
            posts.append({'id': a.id, 'data': datetime.date.today().isoformat(), 'hora': '12:30', 'formato': 'reel', 'loja': 'misto',
                          'tema': 'Top 5 da semana: %d achadinhos que mais caíram de preço' % n, 'canal': 'ig', 'produtos': [i['id'] for i, _ in esc],
                          'status': 'planejado', 'video': 'postagens/%s/reel.mp4' % a.id, 'objetivo': 'descoberta',
                          'nota': 'Protótipo Top 5 da semana (dados reais de quedas.json); revisar antes de agendar.', 'legenda': legenda})
            with open(pf, 'w', encoding='utf-8', newline='\n') as f: f.write(json.dumps(posts, ensure_ascii=False, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())

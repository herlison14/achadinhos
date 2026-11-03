#!/usr/bin/env python3 -I
"""Reel "Caiu de preço" (vertical 1080x1920, ~16 s, sem áudio) feito só com dados reais de dados/quedas.json + itens.json.

Regras: só entra item cuja queda está no histórico (antes -> agora, com datas), cujo preço atual (itens.json) é o preço "agora",
conferido há no máximo 7 dias e com foto local. Nada de desconto inventado: o percentual vem das duas conferências.
Saída: postagens/<id>/reel.mp4 (+ capa.jpg) e a legenda em dados/posts.json como post "planejado" (formato "reel").
O robô ainda NÃO publica Reels: o post só entra na fila depois de revisado.

Uso: python3 -I tools/reels.py [--max 4] [--id AAAA-MM-DD-queda-do-dia] [--sem-registrar]
Precisa de ffmpeg e Pillow; fontes convertidas sozinhas de fonts/*.woff2 (fonttools+brotli).
"""
import argparse, datetime, html, importlib.util, json, os, re, subprocess, sys, tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('cresc', os.path.join(RAIZ, 'tools', 'crescimento.py'))
CR = importlib.util.module_from_spec(spec); spec.loader.exec_module(CR)
C = CR.C
from PIL import Image, ImageDraw

W, H = 1080, 1920
DUR_CAPA, DUR_ITEM, DUR_FIM, XF = 2.6, 3.6, 3.0, 0.4
LOJAS = CR.LOJAS


def br(v):
    return 'R$ ' + v


def pct(antes, agora):
    a = float(antes.replace('.', '').replace(',', '.')); b = float(agora.replace('.', '').replace(',', '.'))
    return int(round((a - b) / a * 100))


def novo():
    img = Image.new('RGB', (W, H), C.LAV); return img, ImageDraw.Draw(img)


def margem(img):
    """Reduz a cena para 94% e centraliza: o zoom suave do vídeo e a interface do Reels não cortam logo, loja nem rodapé."""
    base = Image.new('RGB', (W, H), C.LAV); m = img.resize((int(W * 0.94), int(H * 0.94)), Image.LANCZOS)
    base.paste(m, ((W - m.width) // 2, (H - m.height) // 2)); return base


def cena_capa(n, data):
    img, d = novo(); C.logo(img, d)
    y = 520
    d.text((80, y), 'CAIU DE', font=C.BALOO(190), fill=C.ROXO); y += 250
    d.text((80, y), 'PREÇO', font=C.BALOO(250), fill=C.VERM); y += 360
    d.text((80, y), '%d achadinhos que baixaram' % n, font=C.NUN8(52), fill=C.ROXO2)
    d.text((80, y + 70), 'preços conferidos até %s' % data, font=C.NUN7(40), fill=C.ROXO2)
    C.pilula(d, (80, y + 190), 'DESLIZA E CONFERE', C.NUN8(44), C.ROXO, C.AMARELO)
    d.text((W / 2, 1830), 'Publicidade: links de afiliado', font=C.NUN8(32), fill=C.ROXO, anchor='mm')
    return img


def cena_item(i, q, k, n):
    img, d = novo(); C.logo(img, d); C.etiqueta(d, i['loja'])
    lado = 820
    fr = C.arred(C.encaixar(C.foto(i['id']), lado, 40), 50); img.paste(fr, (130, 190), fr)
    d.ellipse((60, 170, 160, 270), fill=C.AMARELO, outline=C.ROXO, width=6)
    d.text((110, 222), '%d/%d' % (k, n), font=C.BALOO(40), fill=C.ROXO, anchor='mm')
    nome = html.unescape(i['nome']); f = C.NUN8(48); y = 1060
    for l in C.quebrar(d, nome, f, 840, 2): d.text((80, y), l, font=f, fill=C.ROXO); y += 56
    y += 22
    d.text((80, y), 'de ' + br(q['antes']), font=C.NUN7(44), fill=C.ROXO2)
    w = C.larg(d, 'de ' + br(q['antes']), C.NUN7(44)); d.line((80, y + 26, 80 + w, y + 26), fill=C.VERM, width=5)
    d.text((80, y + 56), 'por ' + br(q['agora']), font=C.BALOO(120), fill=C.VERM)
    p = pct(q['antes'], q['agora'])
    C.pilula(d, (700, y - 14), '-%d%%' % p, C.NUN8(56), C.AMARELO, C.ROXO)
    d.text((80, y + 215), 'conferido em %s (antes: %s)' % (datetime.date.fromisoformat(i['conferido']).strftime('%d/%m/%Y'),
           datetime.date.fromisoformat(q['data_antes']).strftime('%d/%m') if q.get('data_antes') else 'conferência anterior'),
           font=C.NUN7(32), fill=C.ROXO2)
    d.text((W / 2, 1830), 'Publicidade: links de afiliado • o preço pode mudar', font=C.NUN7(30), fill=C.ROXO2, anchor='mm')
    return img


def cena_fim(data):
    img, d = novo(); C.logo(img, d)
    for n, l in enumerate(('Quer ver', 'todas as ofertas?')):
        d.text((W / 2, 700 + n * 140), l, font=C.BALOO(118), fill=C.ROXO, anchor='mm')
    fb = C.NUN8(56); w = C.larg(d, 'LINK NA BIO', fb) + 90
    C.pilula(d, ((W - w) / 2, 1030), 'LINK NA BIO', fb, C.ROXO, C.AMARELO)
    d.text((W / 2, 1230), 'achadinhosdobinga.com.br', font=C.NUN8(44), fill=C.ROXO2, anchor='mm')
    d.text((W / 2, 1300), 'Salva e manda pra quem compra online', font=C.NUN7(38), fill=C.ROXO2, anchor='mm')
    d.text((W / 2, 1830), 'Publicidade: links de afiliado', font=C.NUN8(32), fill=C.ROXO, anchor='mm')
    return img


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


def video(cenas, saida):
    """cenas: [(arquivo_png, duração)]. Zoom suave em cada cena + transição de 0,4 s, H.264 yuv420p com trilha de áudio muda."""
    cmd = ['ffmpeg', '-y', '-loglevel', 'error']
    for arq, dur in cenas: cmd += ['-loop', '1', '-t', '%.2f' % (dur + XF), '-i', arq]
    cmd += ['-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo']
    filt, ult, t = [], None, 0.0
    for k, (_, dur) in enumerate(cenas):
        filt.append('[%d:v]scale=1188:2112,zoompan=z=\'min(zoom+0.0004,1.04)\':d=%d:x=\'iw/2-(iw/zoom/2)\':y=\'ih/2-(ih/zoom/2)\':s=%dx%d:fps=30,'
                    'format=yuv420p,setsar=1[v%d]' % (k, int((dur + XF) * 30), W, H, k))
    ult = 'v0'; t = cenas[0][1]
    for k in range(1, len(cenas)):
        filt.append('[%s][v%d]xfade=transition=fade:duration=%.2f:offset=%.2f[x%d]' % (ult, k, XF, t, k)); ult = 'x%d' % k
        t += cenas[k][1]
    total = sum(d for _, d in cenas) + XF
    cmd += ['-filter_complex', ';'.join(filt), '-map', '[%s]' % ult, '-map', '%d:a' % len(cenas), '-t', '%.2f' % total,
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p', '-r', '30', '-c:a', 'aac', '-b:a', '96k',
            '-movflags', '+faststart', saida]
    subprocess.run(cmd, check=True)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--max', type=int, default=4)
    ap.add_argument('--id', default=datetime.date.today().isoformat() + '-queda-do-dia')
    ap.add_argument('--sem-registrar', action='store_true')
    a = ap.parse_args()
    esc = escolher(a.max)
    if len(esc) < 2: print('poucas quedas reais e atuais (%d): nada gerado' % len(esc)); return 1
    n = len(esc); data = max(datetime.date.fromisoformat(i['conferido']) for i, _ in esc).strftime('%d/%m/%Y')
    pasta = os.path.join(RAIZ, 'postagens', a.id); os.makedirs(pasta, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        cenas = []
        capa = margem(cena_capa(n, data)); capa.save(os.path.join(tmp, 'c.png')); cenas.append((os.path.join(tmp, 'c.png'), DUR_CAPA))
        capa.crop((0, 0, W, 1350)).save(os.path.join(pasta, 'capa.jpg'), 'JPEG', quality=90)
        for k, (i, q) in enumerate(esc, 1):
            p = os.path.join(tmp, 'i%d.png' % k); margem(cena_item(i, q, k, n)).save(p); cenas.append((p, DUR_ITEM))
        p = os.path.join(tmp, 'f.png'); margem(cena_fim(data)).save(p); cenas.append((p, DUR_FIM))
        dur = video(cenas, os.path.join(pasta, 'reel.mp4'))
    linhas = []
    for k, (i, q) in enumerate(esc, 1):
        linhas.append('%d. %s: de R$ %s para R$ %s (conferido em %s)' % (k, html.unescape(i['nome']), q['antes'], q['agora'],
                      datetime.date.fromisoformat(i['conferido']).strftime('%d/%m/%Y')))
    legenda = ('Caiu de preço 📉 %d achadinhos que baixaram nas últimas conferências\n\n%s\n\n'
               'O preço pode mudar: confirme na loja antes de comprar.\nTodas as ofertas, com preço e data, no site: link na bio 🔗\n'
               'Salva e manda pra quem compra online.\n\nPublicidade: links de afiliado.\n\n#caiudepreço #achadinhos #ofertas #comprasonline') % (n, '\n'.join(linhas))
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

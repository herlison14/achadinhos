#!/usr/bin/env python3 -I
"""Stories (vertical 1080x1920) do @achadinhosdobinga com dados reais, publicados pelo robô (tools/instagram.py, formato "story").

Tipos:
  oferta  - 1 produto com foto local, preço conferido há no máximo 3 dias (data na imagem), "link na bio".
  queda   - item de dados/quedas.json (antes -> agora e % vêm do histórico), conferido há no máximo 3 dias.
  site    - sem preço: o que o site faz (busca, preço com data de conferência, "Caiu de preço").
Regras: nunca inventar preço/desconto; a trava do robô confere de novo o preço no momento de publicar (máx. 7 dias).
Story não leva legenda no Instagram; o campo "legenda" em posts.json é só a descrição interna (com preço e o aviso de afiliado).
Áreas de segurança: o Instagram cobre ~250 px no topo e ~340 px embaixo; o conteúdo fica entre elas.

Uso: python3 -I tools/stories.py --dias 7 [--por-dia 2] [--inicio AAAA-MM-DD] [--agora HH:MM] [--sem-registrar] [--amostra PASTA]
  --agora HH:MM: cria também um Story para hoje nesse horário (ex.: publicação urgente).
Fontes: convertidas sozinhas de fonts/*.woff2 (fonttools+brotli). Precisa de Pillow.
"""
import argparse, datetime, html, importlib.util, json, os, random, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))


def _carrega(nome):
    s = importlib.util.spec_from_file_location(nome, os.path.join(RAIZ, 'tools', nome + '.py'))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


CR = _carrega('crescimento')
getattr(CR, 'garantir_fontes', lambda: None)()
CD = _carrega('cards')
from PIL import Image, ImageDraw

W, H = 1080, 1920
ROXO, AMARELO, VERM, LAV, ROXO2 = CD.ROXO, CD.AMARELO, CD.VERM, CD.LAV, CD.ROXO2
HORAS = ['11:30', '18:30']          # slots próprios de Story (não colidem com feed/Reels)
BRT = datetime.timezone(datetime.timedelta(hours=-3))
MAX_IDADE = 3
J = lambda *p: os.path.join(RAIZ, *p)


def ler(p, pad):
    try:
        return json.load(open(J(*p), encoding='utf-8'))
    except FileNotFoundError:
        return pad


def dbr(iso):
    a = iso.split('-'); return '%s/%s/%s' % (a[2], a[1], a[0])


def limpa(t):
    return CD.limpar(html.unescape(t))


def base():
    img = Image.new('RGB', (W, H), LAV); d = ImageDraw.Draw(img)
    m = Image.open(J('img', 'marca.webp')).convert('RGB').resize((84, 84), Image.LANCZOS)
    mk = Image.new('L', (84, 84), 0); ImageDraw.Draw(mk).ellipse((0, 0, 83, 83), fill=255)
    img.paste(m, (80, 270), mk)
    d.text((180, 280), 'achadinhos', font=CD.BALOO(36), fill=ROXO)
    d.text((180, 312), 'do binga', font=CD.BALOO(36), fill=VERM)
    return img, d


def etiqueta(d, loja):
    nome, bg, fg = CD.LOJAS[loja]
    f = CD.NUN8(34); w = CD.larg(d, nome, f) + 56
    d.rounded_rectangle((W - 80 - w, 272, W - 80, 338), radius=33, fill=bg)
    d.text((W - 80 - w / 2, 306), nome, font=f, fill=fg, anchor='mm')


def rodape(d, y, texto):
    d.text((W / 2, y), texto, font=CD.NUN7(28), fill=ROXO2, anchor='mm')
    d.text((W / 2, y + 44), 'Publicidade: links de afiliado', font=CD.NUN8(28), fill=ROXO, anchor='mm')


def cta(d, y, txt='LINK NA BIO'):
    f = CD.NUN8(46); w = CD.larg(d, txt, f) + 80
    CD.pilula(d, ((W - w) / 2, y), txt, f, ROXO, AMARELO)


def card_produto(it, antes=None, pct=None):
    img, d = base(); etiqueta(d, it['loja'])
    lado = 860
    fr = CD.arred(CD.encaixar(CD.foto(it['id']), lado, 40), 50); img.paste(fr, ((W - lado) // 2, 400), fr)
    if pct:
        d.ellipse((W - 330, 360, W - 130, 560), fill=VERM, outline='white', width=8)
        d.text((W - 230, 460), '-%d%%' % pct, font=CD.BALOO(78), fill='white', anchor='mm')
    f = CD.NUN8(46); ls = CD.quebrar(d, limpa(it['nome']), f, 900, 2); y = 1300
    for l in ls:
        d.text((W / 2, y), l, font=f, fill=ROXO, anchor='mm'); y += 56
    if antes:
        t = 'R$ ' + antes; ft = CD.NUN7(40); tw = CD.larg(d, t, ft)
        d.text((W / 2, 1418), t, font=ft, fill=ROXO2, anchor='mm'); d.line((W / 2 - tw / 2, 1418, W / 2 + tw / 2, 1418), fill=ROXO2, width=4)
    d.text((W / 2, 1500 if antes else 1470), 'R$ ' + it['preco'], font=CD.BALOO(110), fill=VERM, anchor='mm')
    cta(d, 1570)
    rodape(d, 1690 if False else 1700, 'Preço conferido em %s • pode mudar' % dbr(it['conferido']))
    return img


def card_site():
    img, d = base()
    f = CD.BALOO(104); y = 520
    for l in ('Preço com', 'data de', 'conferência'):
        d.text((W / 2, y), l.upper(), font=f, fill=ROXO, anchor='mm'); y += 120
    for i, t in enumerate(('Busque pelo produto no site', 'Veja o que caiu de preço', 'Compare as 5 lojas num só lugar')):
        d.rounded_rectangle((100, 940 + i * 120, W - 100, 1040 + i * 120), radius=34, fill='white')
        d.text((W / 2, 990 + i * 120), t, font=CD.NUN8(38), fill=ROXO, anchor='mm')
    cta(d, 1360)
    d.text((W / 2, 1500), 'Confira o valor na loja antes de comprar.', font=CD.NUN7(30), fill=ROXO2, anchor='mm')
    d.text((W / 2, 1560), 'Publicidade: links de afiliado', font=CD.NUN8(28), fill=ROXO, anchor='mm')
    return img


def tem_foto(pid):
    return os.path.exists(J('img', pid + '.webp')) or os.path.exists(J('img', 'cards', pid + '.jpg'))


def escolher(itens, posts, hoje, n, tipos_dia):
    """Itens com foto, conferidos há ≤ MAX_IDADE dias, sem aparecer em Story nos últimos 14 dias; uma loja por vez."""
    usados = {}
    for p in posts:
        if p.get('formato') == 'story':
            for pid in p.get('produtos', []):
                usados[pid] = max(usados.get(pid, ''), p['data'])
    lim = (hoje - datetime.timedelta(days=14)).isoformat()
    quedas = {q['id']: q for q in ler(('dados', 'quedas.json'), [])}
    ok = []
    for i in itens:
        idade = (hoje - datetime.date.fromisoformat(i['conferido'])).days
        if idade <= MAX_IDADE and tem_foto(i['id']) and usados.get(i['id'], '0') < lim:
            ok.append(i)
    random.Random(hoje.toordinal()).shuffle(ok)
    ok.sort(key=lambda i: (i['id'] not in quedas, ))      # quedas reais primeiro
    por_loja, saida, ultima = {}, [], None
    for i in ok:
        por_loja.setdefault(i['loja'], []).append(i)
    lojas = sorted(por_loja, key=lambda l: -len(por_loja[l]))
    while len(saida) < n and any(por_loja.values()):
        for l in lojas:
            if por_loja[l] and l != ultima and len(saida) < n:
                saida.append(por_loja[l].pop(0)); ultima = l
        ultima = None
    return saida, quedas


def refazer():
    """Atualiza imagem e descrição dos Stories pendentes (agendado/planejado) com o preço atual; roda depois de vigia.py atualizar."""
    posts = ler(('dados', 'posts.json'), []); itens = {i['id']: i for i in ler(('dados', 'itens.json'), [])}
    quedas = {q['id']: q for q in ler(('dados', 'quedas.json'), [])}
    n = 0
    for p in posts:
        if p.get('formato') != 'story' or p.get('status') not in ('agendado', 'planejado') or len(p.get('produtos', [])) != 1:
            continue
        it = itens.get(p['produtos'][0])
        if not it or not tem_foto(it['id']):
            continue
        q = quedas.get(it['id']); queda = bool(q and q.get('agora') == it['preco'] and q.get('pct', 0) > 0)
        leg = 'Story: %s: R$ %s (conferido em %s)%s. Publicidade: links de afiliado.' % (
            limpa(it['nome']), it['preco'], dbr(it['conferido']), (' — antes R$ %s, queda de %d%% no histórico' % (q['antes'], q['pct'])) if queda else '')
        if leg == p.get('legenda'):
            continue
        (card_produto(it, q['antes'], q['pct']) if queda else card_produto(it)).save(J(p['imagens'][0]), quality=92, optimize=True)
        p['legenda'] = leg; n += 1
        print('refeito', p['id'])
    if n:
        json.dump(posts, open(J('dados', 'posts.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        open(J('dados', 'posts.json'), 'a').write('\n')
    print('%d story(s) atualizados.' % n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dias', type=int, default=7); ap.add_argument('--por-dia', type=int, default=2)
    ap.add_argument('--inicio'); ap.add_argument('--agora'); ap.add_argument('--sem-registrar', action='store_true')
    ap.add_argument('--amostra'); ap.add_argument('--refazer', action='store_true', help='redesenha os cards dos Stories ainda não publicados com o preço atual de itens.json')
    a = ap.parse_args()
    agora = datetime.datetime.now(BRT); hoje = agora.date()
    if a.refazer:
        return refazer()
    ini = datetime.date.fromisoformat(a.inicio) if a.inicio else hoje + datetime.timedelta(days=1)
    itens = ler(('dados', 'itens.json'), []); posts = ler(('dados', 'posts.json'), [])
    existentes = {p['id'] for p in posts}
    slots = []                                      # (data, hora)
    if a.agora:
        slots.append((hoje, a.agora))
    for k in range(a.dias):
        d = ini + datetime.timedelta(days=k)
        for h in HORAS[:a.por_dia]:
            slots.append((d, h))
    novos = []
    prod, quedas = escolher(itens, posts, hoje, sum(1 for s in slots), None)
    pi = iter(prod)
    for n, (dia, hora) in enumerate(slots):
        # o último slot de cada dia alterna para o Story do site (sem preço) a cada 3 dias
        usa_site = (hora == HORAS[-1] and dia.toordinal() % 3 == 0)
        if usa_site:
            sid = '%s-story-site' % dia.isoformat(); tema = 'Story: preço com data de conferência'; prods = []
            ver = lambda: card_site(); leg = 'Story sem preço: o que o site faz (busca, quedas de preço, 5 lojas). Publicidade: links de afiliado.'
        else:
            it = next(pi, None)
            if not it:
                print('sem item elegível para', dia, hora); continue
            q = quedas.get(it['id'])
            queda = bool(q and q.get('agora') == it['preco'] and q.get('pct', 0) > 0)
            sid = '%s-story-%s%s' % (dia.isoformat(), it['id'], '-%s' % hora.replace(':', '') if False else '')
            tema = 'Story: %s' % limpa(it['nome'])[:60]; prods = [it['id']]
            ver = (lambda it=it, q=q, queda=queda: card_produto(it, q['antes'], q['pct']) if queda else card_produto(it))
            leg = 'Story: %s: R$ %s (conferido em %s)%s. Publicidade: links de afiliado.' % (
                limpa(it['nome']), it['preco'], dbr(it['conferido']), (' — antes R$ %s, queda de %d%% no histórico' % (q['antes'], q['pct'])) if queda else '')
        if sid in existentes:
            continue
        if a.amostra:
            os.makedirs(a.amostra, exist_ok=True); ver().save(os.path.join(a.amostra, sid + '.jpg'), quality=92); print('amostra', sid); continue
        os.makedirs(J('postagens', sid), exist_ok=True)
        ver().save(J('postagens', sid, '01.jpg'), quality=92, optimize=True)
        novos.append(dict(id=sid, data=dia.isoformat(), hora=hora, formato='story', canal='ig', tema=tema, produtos=prods,
                          imagens=['postagens/%s/01.jpg' % sid], legenda=leg, status='agendado', objetivo='story', sem_preco=not prods))
        print('story', sid, dia, hora)
    if novos and not a.sem_registrar:
        posts.extend(novos)
        json.dump(posts, open(J('dados', 'posts.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        open(J('dados', 'posts.json'), 'a').write('\n')
    print('%d story(s) %s.' % (len(novos), 'criados' if not a.sem_registrar else 'gerados (sem registrar)'))


if __name__ == '__main__':
    main()

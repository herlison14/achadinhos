#!/usr/bin/env python3
"""Confere se TODOS os meios de visualização refletem dados/itens.json (fonte única).

  python3 -I tools/sincronia.py           confere e mostra o relatório (sai com 1 se houver ERRO)

Confere: página (index.html), histórico de preços, quedas, calendário de posts,
posts agendados no Instagram (preço da legenda) e itens sem conferência recente.
O painel (/painel/), o canal do Telegram, os textos do WhatsApp e o Instagram leem
dados/itens.json na hora de rodar; por isso o que importa é a página estar gerada e os
dados coerentes. Sem dependências."""
import html, json, os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda *p: os.path.join(RAIZ, *p)


def ler(p, padrao=None):
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return padrao


# Padrões de segredo que nunca podem aparecer em arquivos do repositório (público).
SEGREDOS = [
    ('token do GitHub', r'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}'),
    ('token do Telegram', r'\b\d{8,10}:AA[A-Za-z0-9_-]{30,}'),
    ('token da Meta/Instagram', r'\bEAA[A-Za-z0-9]{40,}'),
    ('chave privada', r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
    ('chave de API', r'\bsk-[A-Za-z0-9]{20,}|\bAKIA[0-9A-Z]{16}'),
    ('segredo/senha escrito no código',
     r'(?i)(totp_secret|report_key|ig_token|password|senha)\s*[:=]\s*["\'][A-Za-z0-9+/=_-]{12,}["\']'),
]
IGNORAR_DIRS = {'.git', 'fonts', '__pycache__', 'node_modules'}


def varrer_segredos():
    achados = []
    padroes = [(n, re.compile(r)) for n, r in SEGREDOS]
    for base, dirs, arqs in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d not in IGNORAR_DIRS]
        for a in arqs:
            if a == 'sincronia.py' or a.lower().endswith(('.png', '.jpg', '.jpeg', '.woff', '.woff2', '.ico')):
                continue
            c = os.path.join(base, a)
            try:
                txt = open(c, encoding='utf-8', errors='ignore').read()
            except OSError:
                continue
            for nome, rx in padroes:
                if rx.search(txt):
                    achados.append('%s em %s' % (nome, os.path.relpath(c, RAIZ)))
    return achados


def main():
    erros, avisos = [], []
    itens = ler(J('dados', 'itens.json'), [])
    hist = ler(J('dados', 'historico.json'), {})
    quedas = ler(J('dados', 'quedas.json'), [])
    posts = ler(J('dados', 'posts.json'), [])
    try:
        pagina = open(J('index.html'), encoding='utf-8').read()
    except Exception:
        pagina = ''
        erros.append('index.html não encontrado')
    if not itens:
        erros.append('dados/itens.json vazio ou ilegível')

    # 1) página x itens.json
    lis = []
    for bloco in re.findall(r'<li class="it">(.*?)</li>', pagina, re.S):
        mh = re.search(r'<a href="([^"]+)"', bloco)
        mp = re.search(r'<span class="pr">.*?<b>([^<]+)</b>', bloco, re.S)
        if mh and mp:
            lis.append((mh.group(1), mp.group(1)))
    na_pag = {h: p for h, p in lis}
    ids_ok = {}
    for i in itens:
        h = html.escape(i['href'], quote=True)
        ids_ok[i['id']] = i
        if h not in na_pag and i['href'] not in na_pag:
            erros.append('fora da página: %s (%s)' % (i['nome'][:40], i['loja']))
            continue
        pr = na_pag.get(h) or na_pag.get(i['href'])
        if 'R$ ' + i['preco'] not in pr:
            erros.append('preço diferente na página: %s (itens.json R$ %s, página %s)' % (i['nome'][:40], i['preco'], pr))
    hrefs = {html.escape(i['href'], quote=True) for i in itens} | {i['href'] for i in itens}
    for h in na_pag:
        if h not in hrefs:
            erros.append('na página mas não em itens.json: ' + h[:60])
    m = re.search(r'id="n-of">(\d+)<', pagina)
    if m and int(m.group(1)) != len(itens):
        erros.append('contador da página (%s) diferente de itens.json (%d)' % (m.group(1), len(itens)))

    # 1b) link de afiliado em todo item (existente ou novo)
    for i in itens:
        h, l = i['href'], i['loja']
        if l == 'amazon':
            ok = ('amzn.to/' in h) or ('amazon.com.br/' in h and 'tag=herlisonsanto-20' in h)
        elif l == 'meli':
            ok = 'meli.la/' in h
        elif l == 'shopee':
            ok = 's.shopee.com.br/' in h
        elif l == 'aliexpress':
            ok = 's.click.aliexpress.com/e/' in h
        elif l == 'magalu':
            ok = 'magazinevoce.com.br/magazinein_400408/' in h
        else:
            ok = False
        if not ok:
            erros.append('link sem afiliado/inválido: %s (%s)' % (i['nome'][:40], l))

    # 2) histórico
    for i in itens:
        h = hist.get(i['id'])
        if not h:
            erros.append('sem histórico: ' + i['nome'][:40])
        elif h[-1][1] != i['preco']:
            avisos.append('último preço do histórico (%s) difere do atual (%s): %s' % (h[-1][1], i['preco'], i['nome'][:40]))

    # 3) quedas
    for q in (quedas if isinstance(quedas, list) else []):
        qid = q.get('id') if isinstance(q, dict) else None
        if qid and qid not in ids_ok:
            avisos.append('queda de item que não existe mais: ' + str(qid))

    # 4) calendário e Instagram
    for p in posts:
        for pid in p.get('produtos', []):
            if pid not in ids_ok:
                avisos.append('post %s cita item removido: %s' % (p['id'], pid))
        if p.get('status') in ('planejado', 'agendado') and p.get('legenda'):
            for pid in p.get('produtos', []):
                it = ids_ok.get(pid)
                if it and 'R$ ' + it['preco'] not in p['legenda']:
                    avisos.append('legenda do post %s sem o preço atual de %s (R$ %s): atualize antes de agendar' % (p['id'], it['nome'][:30], it['preco']))

    # 5) idade da conferência
    import datetime
    hoje = datetime.date.today()
    velhos = [i for i in itens if (hoje - datetime.date.fromisoformat(i['conferido'])).days > 7]
    if velhos:
        avisos.append('%d item(ns) sem conferência há mais de 7 dias (não vão ao Telegram/Instagram)' % len(velhos))

    for s in varrer_segredos():
        erros.append('possível segredo no repositório público: ' + s)

    por_loja = {}
    for i in itens:
        por_loja[i['loja']] = por_loja.get(i['loja'], 0) + 1
    print('itens: %d  %s' % (len(itens), '  '.join('%s %d' % (k, v) for k, v in sorted(por_loja.items()))))
    print('na página: %d  histórico: %d  posts: %d' % (len(lis), len(hist), len(posts)))
    for a in avisos:
        print('AVISO:', a)
    for e in erros:
        print('ERRO:', e)
    print('SINCRONIA: %s' % ('FALHOU (%d erro(s))' % len(erros) if erros else 'OK'))
    return 1 if erros else 0


if __name__ == '__main__':
    sys.exit(main())

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

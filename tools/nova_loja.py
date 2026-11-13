#!/usr/bin/env python3
"""Cadastra uma loja nova da Awin em TODOS os pontos do sistema, de uma vez.

Uso:
  python3 -I tools/nova_loja.py SLUG "Nome" PROGRAMA DOMINIO[,DOMINIO2] FOTOS[,FOTOS2] \
      --cor "#FUNDO,#TEXTO" --etiqueta "#FUNDO,#TEXTO" [--prep na|no] [--fora-dos-canais] [--testar]

Exemplo:
  python3 -I tools/nova_loja.py mizuno "Mizuno" 51271 mizuno.com.br mizunobr.vteximg.com.br \
      --cor "#001E62,#FFFFFF" --etiqueta "#E6ECF7,#001E62" --prep na

O que ele atualiza (todos os lugares onde as lojas aparecem):
  tools/vigia.py (NOMES, AWIN, CTA), tools/paginas.py, tools/canais.py, tools/telegram_post.py,
  tools/crescimento.py, tools/vendas.py, tools/pinterest.py, tools/auditor.py, tools/cards.py,
  tools/sincronia.py (domínio e regra do link Awin), index.html (nomes, mapa de domínios, cor da
  etiqueta, opção do seletor), painel/index.html, cliques.js, worker/bot/worker.js,
  worker/bloco_2_api_ganhos.js, _headers (img-src das fotos) e dados/lojas_awin.json (registro).

Depois: pôr os itens em dados/itens.json, rodar vigia.py build e sincronia.py.
Os dois arquivos de worker/ precisam ser colados à mão no Cloudflare (não há deploy automático).
Âncora: a loja "hope" (já cadastrada). Cada inserção entra logo depois da entrada da Hope.
"""
import argparse, json, os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ler(p):
    with open(os.path.join(RAIZ, p), encoding='utf-8') as f:
        return f.read()


def gravar(p, s):
    with open(os.path.join(RAIZ, p), 'w', encoding='utf-8', newline='\n') as f:
        f.write(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('slug'); ap.add_argument('nome'); ap.add_argument('programa')
    ap.add_argument('dominios'); ap.add_argument('fotos')
    ap.add_argument('--cor', required=True, help='cor do card: "#fundo,#texto"')
    ap.add_argument('--etiqueta', required=True, help='cor da etiqueta no site: "#fundo,#texto"')
    ap.add_argument('--prep', default='na', choices=['na', 'no'])
    ap.add_argument('--fora-dos-canais', action='store_true', help='loja que proíbe Telegram/WhatsApp')
    ap.add_argument('--testar', action='store_true', help='só mostra o que mudaria')
    a = ap.parse_args()
    s, n = a.slug, a.nome
    if not re.fullmatch(r'[a-z0-9]+', s): sys.exit('slug só com letras minúsculas e números')
    doms = [d.strip() for d in a.dominios.split(',') if d.strip()]
    fotos = [d.strip() for d in a.fotos.split(',') if d.strip()]
    cb, ct = [c.strip() for c in a.cor.split(',')]
    eb, et = [c.strip() for c in a.etiqueta.split(',')]
    cta = 'Ver %s %s' % (a.prep, n)
    pre = '%s %s' % (a.prep, n)
    ja = 0
    mud = []

    def troca(arq, ancora, novo, chave=None):
        """Insere `novo` logo depois da primeira ocorrência de `ancora` (regex). Pula se `chave` já existe."""
        nonlocal ja
        t = ler(arq)
        if chave and chave in t:
            ja += 1; return
        m = re.search(ancora, t)
        if not m: sys.exit('ÂNCORA NÃO ENCONTRADA em %s: %s' % (arq, ancora))
        t2 = t[:m.end()] + novo + t[m.end():]
        mud.append(arq)
        if not a.testar: gravar(arq, t2)

    q = lambda c: c  # legibilidade
    # nomes (dicionários Python com aspas simples e duplas)
    for arq in ('tools/vigia.py', 'tools/paginas.py', 'tools/crescimento.py', 'tools/pinterest.py'):
        troca(arq, r"'hope': 'Hope Lingerie'", ", '%s': '%s'" % (s, n), "'%s': '%s'" % (s, n))
    for arq in ('tools/canais.py', 'tools/telegram_post.py', 'tools/vendas.py'):
        troca(arq, r'"hope": "Hope Lingerie"', ', "%s": "%s"' % (s, n), '"%s": "%s"' % (s, n))
    # vigia: domínio -> loja e texto do botão
    troca('tools/vigia.py', r"'hopeoficial\.com\.br': 'hope'", ''.join(", '%s': '%s'" % (d, s) for d in doms), "'%s': '%s'" % (doms[0], s))
    troca('tools/vigia.py', r"'hope': 'Ver na Hope'", ", '%s': '%s'" % (s, cta), "'%s': '%s'" % (s, cta))
    # cards: cor e preposição
    troca('tools/cards.py', r"'hope': \('Hope', '#[0-9A-Fa-f]{6}', '#[0-9A-Fa-f]{6}'\)", ", '%s': ('%s', '%s', '%s')" % (s, n, cb, ct), "'%s': ('%s'" % (s, n))
    troca('tools/cards.py', r"'Hope': 'na Hope'", ", '%s': '%s'" % (n, pre), "'%s': '%s'" % (n, pre))
    # sincronia: domínio e regra do link Awin
    troca('tools/sincronia.py', r"\('hopeoficial\.com\.br', 'hope'\)", ''.join(", ('%s', '%s')" % (d, s) for d in doms), "('%s', '%s')" % (doms[0], s))
    troca('tools/sincronia.py', r"'puma', 'hope'", ", '%s'" % s, "'hope', '%s'" % s)
    # auditor
    troca('tools/auditor.py', r'"puma", "hope"', ', "%s"' % s, '"hope", "%s"' % s)
    # site e painel (JavaScript)
    for arq in ('index.html', 'painel/index.html'):
        troca(arq, r"hope:'Hope Lingerie'", ",%s:'%s'" % (s, n), ",%s:'%s'" % (s, n))
    troca('index.html', r"'hopeoficial\.com\.br':'hope'", ''.join(",'%s':'%s'" % (d, s) for d in doms), "'%s':'%s'" % (doms[0], s))
    troca('index.html', r"\.lj-hope\{[^}]*\}", "\n.lj-%s{background:%s;color:%s}" % (s, eb, et), '.lj-%s{' % s)
    troca('index.html', r'<option value="hope">Hope Lingerie</option>', '<option value="%s">%s</option>' % (s, n), '<option value="%s">' % s)
    troca('cliques.js', r"'hopeoficial\.com\.br': 'hope'", ''.join(", '%s': '%s'" % (d, s) for d in doms), "'%s': '%s'" % (doms[0], s))
    # Cloudflare (colar à mão)
    troca('worker/bot/worker.js', r"hope: 'Hope Lingerie'", ", %s: '%s'" % (s, n), " %s: '%s'" % (s, n))
    troca('worker/bloco_2_api_ganhos.js', r"'puma', 'hope'", ", '%s'" % s, "'hope', '%s'" % s)
    # CSP: domínios das fotos
    for f in fotos:
        troca('_headers', r"img-src 'self' data:", ' https://' + f, ' https://%s' % f)
    # canais proibidos (ex.: adidas)
    if a.fora_dos_canais:
        troca('tools/canais.py', r'FORA_DOS_CANAIS = \{[^}]*', ', "%s"' % s, '"%s"' % s)
    # registro
    reg_p = 'dados/lojas_awin.json'
    reg = json.loads(ler(reg_p)) if os.path.exists(os.path.join(RAIZ, reg_p)) else {}
    reg[s] = {'nome': n, 'programa': a.programa, 'dominios': doms, 'fotos': fotos, 'cta': cta,
              'cor_card': [cb, ct], 'etiqueta': [eb, et], 'fora_dos_canais': a.fora_dos_canais}
    if not a.testar:
        gravar(reg_p, json.dumps(reg, ensure_ascii=False, indent=1) + '\n')
    print('%s: %d arquivo(s) alterado(s), %d ponto(s) já tinham a loja.' % (n, len(set(mud)), ja))
    for m in sorted(set(mud)): print('  ' + m)
    print('Falta: itens em dados/itens.json (link https://www.awin1.com/cread.php?awinmid=%s&awinaffid=3147693&ued=...), '
          'vigia.py build, sincronia.py e colar worker/bot/worker.js e worker/bloco_2_api_ganhos.js no Cloudflare.' % a.programa)


if __name__ == '__main__':
    main()

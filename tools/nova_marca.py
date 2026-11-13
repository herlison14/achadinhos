#!/usr/bin/env python3
"""Cria uma marca nova com a MESMA estrutura do Achadinhos do Binga (site, painel, robôs, Workers, fluxos).

Uso:
  python3 -I tools/nova_marca.py modelo/marca.exemplo.json /caminho/da/pasta-nova [--sobrescrever]

O que faz:
  1. Copia o código (tools/, worker/, painel/, .github/workflows/, index.html, cliques.js, _headers,
     privacidade.html, fontes e ícones) para a pasta nova.
  2. Troca tudo que é do Achadinhos pelos dados da marca (nome, domínio, Instagram, Telegram,
     repositório, Workers, tags de afiliado), na ordem certa (do mais específico ao mais genérico).
  3. Zera os dados (itens, histórico, posts, métricas...) e não copia nada que seja conteúdo do
     Achadinhos (fotos de produtos, posts, Reels, canal do WhatsApp, Natal, Awin, Flow).
  4. Escreve o CLAUDE.md da marca nova a partir de modelo/CLAUDE.modelo.md.
  5. Confere: nenhum vestígio do Achadinhos fora da lista de exceções.

Depois, siga modelo/REPLICAR.md (contas, segredos, Workers, logo, cores, primeiros produtos).
Nada de segredo entra no marca.json: tokens e chaves ficam só no GitHub Secrets e no Cloudflare.
"""
import argparse, json, os, re, shutil, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# O que copiar (pastas e arquivos de código/estrutura).
COPIAR = [
    'tools', 'worker', 'painel', '.github/workflows', 'fonts',
    'index.html', 'cliques.js', '_headers', 'privacidade.html', 'fontes.css', 'robots.txt',
    'dados/LEIAME.md',
    'img/marca.webp', 'img/og.jpg', 'img/favicon-32.png', 'img/favicon-192.png', 'img/apple-touch-icon.png',
]
IGNORAR = {'__pycache__'}
NAO_COPIAR = {os.path.join('tools', 'nova_marca.py')}  # ferramenta de criar marca, não roda na marca nova
TEXTO = {'.py', '.js', '.html', '.css', '.md', '.yml', '.yaml', '.json', '.txt', '.webmanifest', ''}

# Dados zerados (mesmo tipo que o sistema espera).
DADOS_VAZIOS = {
    'itens.json': [], 'historico.json': {}, 'posts.json': [], 'quedas.json': [], 'reels.json': [],
    'crescimento.json': [], 'fotos_urls.json': {}, 'canais.json': {'enviados': []},
    'lojas_awin.json': {}, 'metricas.json': {}, 'destaques.json': {}, 'estrategia.json': {},
    'tendencias.json': {}, 'auditoria.json': {},
}

OBRIGATORIOS = ['nome', 'nome_curto', 'linha2_logo', 'prefixo', 'dominio', 'instagram', 'github_usuario',
                'github_repo', 'cloudflare_subdominio', 'amazon_tag']


def substituicoes(m):
    """Lista ordenada (específico -> genérico) de trocas Achadinhos -> marca nova."""
    p = m['prefixo']
    tg_canal = m.get('telegram_canal') or m['instagram']
    tg_bot = m.get('telegram_bot') or (p + '_bot')
    sub = m['cloudflare_subdominio']
    repo = m['github_usuario'] + '/' + m['github_repo']
    t = [
        # endereços completos primeiro
        ('cliques-binga.herlison14.workers.dev', p + '-cliques.' + sub + '.workers.dev'),
        ('bot-binga.herlison14.workers.dev', p + '-bot.' + sub + '.workers.dev'),
        ('agendador-binga.herlison14.workers.dev', p + '-agendador.' + sub + '.workers.dev'),
        ('herlison14.workers.dev', sub + '.workers.dev'),
        ('achadinhos-4tf.pages.dev', m.get('painel_pages') or (p + '.pages.dev')),
        ('raw.githubusercontent.com/herlison14/achadinhos', 'raw.githubusercontent.com/' + repo),
        ('herlison14/achadinhos', repo),
        ('herlison14.github.io/achadinhos', m['github_usuario'] + '.github.io/' + m['github_repo']),
        ('achadinhosdobinga.com.br', m['dominio']),
        ('instagram.com/achadinhosdobinga', 'instagram.com/' + m['instagram']),
        ('ig.me/m/achadinhosdobinga', 'ig.me/m/' + m['instagram']),
        ('t.me/achadinhosdobinga', 't.me/' + tg_canal),
        ('achadinhosbinga_bot', tg_bot),
        ('@achadinhosdobinga', '@' + m['instagram']),
        ('achadinhosdobinga', m['instagram']),
        # Workers
        ('cliques-binga', p + '-cliques'),
        ('bot-binga', p + '-bot'),
        ('agendador-binga', p + '-agendador'),
        # contas de afiliado (sem segredo: são ids públicos que aparecem nos links)
        ('herlisonsanto-20', m['amazon_tag']),
        ('awinaffid=3147693', 'awinaffid=' + (m.get('awin_publisher') or 'SEU_ID_AWIN')),
        ('3147693', m.get('awin_publisher') or 'SEU_ID_AWIN'),
        ('18306050983', m.get('shopee_afiliado') or 'SEU_ID_SHOPEE'),
        # nome da marca
        ('Achadinhos do Binga', m['nome']),
        ('achadinhos do binga', m['nome'].lower()),
        ('ACHADINHOS DO BINGA', m['nome'].upper()),
        ('Herlison', m['dono']),
        ('Painel Binga', 'Painel ' + m['nome_curto']),
        ("'do binga'", repr(m['linha2_logo'])),
        ('achadinhos-publicador', p + '-publicador'),
        ('achadinhos-auditor', p + '-auditor'),
        ('achadinhos-bot', p + '-bot'),
        ('Achadinhos', m['nome_curto']),
        ('ACHADINHOS', m['nome_curto'].upper()),
        ('achadinhos', p),
        ('Binga', m['nome_curto']),
        ('binga', p),
    ]
    return t


def copiar(dest):
    for item in COPIAR:
        o = os.path.join(RAIZ, item)
        d = os.path.join(dest, item)
        if not os.path.exists(o):
            continue
        os.makedirs(os.path.dirname(d), exist_ok=True)
        if os.path.isdir(o):
            shutil.copytree(o, d, ignore=shutil.ignore_patterns(*IGNORAR), dirs_exist_ok=True)
        else:
            shutil.copy2(o, d)
    for rel in NAO_COPIAR:
        p = os.path.join(dest, rel)
        if os.path.exists(p):
            os.remove(p)


def trocar(dest, trocas):
    mudados = 0
    for raiz, pastas, arqs in os.walk(dest):
        pastas[:] = [x for x in pastas if x not in IGNORAR and x != 'fonts']
        for a in arqs:
            if os.path.splitext(a)[1] not in TEXTO:
                continue
            p = os.path.join(raiz, a)
            try:
                s = open(p, encoding='utf-8').read()
            except UnicodeDecodeError:
                continue
            n = s
            for velho, novo in trocas:
                n = n.replace(velho, novo)
            if n != s:
                open(p, 'w', encoding='utf-8').write(n)
                mudados += 1
    return mudados


def esvaziar_site(dest):
    """Tira o CATÁLOGO DE PRODUTOS da marca original do index.html copiado (nomes, preços, links
    reais de afiliado) — fica só a casca do template. Os mesmos marcadores que `vigia.py build`
    usa continuam no lugar, prontos para a marca nova gerar sua própria página com seus próprios
    itens. Sem isso, o site publicado mostraria o catálogo de outra marca com os preços dela como
    se fossem conferidos por esta."""
    p = os.path.join(dest, 'index.html')
    if not os.path.exists(p):
        return
    h = open(p, encoding='utf-8').read()

    sec = re.compile(r'(<h2>([^<]+)</h2>\s*<ul>)(.*?)(</ul>)', re.S)
    h = sec.sub(lambda m: m.group(1) + m.group(4), h)

    vazio = {'@context': 'https://schema.org', '@graph': []}
    h, nld = re.subn(r'(<!--ld-inicio-->).*?(<!--ld-fim-->)',
                      lambda m: m.group(1) + '<script type="application/ld+json">'
                      + json.dumps(vazio) + '</script>' + m.group(2), h, flags=re.S)

    h, n1 = re.subn(r'(<b id="n-of2">)\d+(</b> ofertas em <b id="n-lj">)\d+(</b>)',
                     r'\g<1>0\g<2>0\g<3>', h)
    h, n2 = re.subn(r'(<b id="n-of">)\d+(</b>.*?com preço conferido em )[^<]*?(\.</p>)',
                     r'\g<1>0\g<2>nenhum item ainda\g<3>', h, flags=re.S)
    h, n3 = re.subn(r'(Preços e estoque são os conferidos em )[^<]*?( e podem ter mudado\.)',
                     r'\g<1>nenhum item ainda\g<2>', h)
    h, n4 = re.subn(r'(<p class="aviso"[^>]*>Publicidade: estes são links de afiliado da )[^<]*?( e eu posso receber)',
                     r'\g<1>nenhuma loja ainda\g<2>', h)
    h, npg = re.subn(r'(<!--paginas-inicio-->).*?(<!--paginas-fim-->)', r'\1\2', h, flags=re.S)
    h = re.sub(r'(em |de )\d+( lojas)', r'\g<1>0\g<2>', h)  # mesma troca que vigia.py build faz no fim

    open(p, 'w', encoding='utf-8', newline='\n').write(h)
    faltou = [n for n, ok in [('ld-json', nld), ('contador', n1), ('data', n2),
                               ('rodapé datas', n3), ('aviso lojas', n4), ('páginas', npg)] if ok != 1]
    if faltou:
        print('AVISO: não consegui limpar no index.html: %s (confira à mão antes de publicar)' % ', '.join(faltou))


def zerar_dados(dest):
    os.makedirs(os.path.join(dest, 'dados'), exist_ok=True)
    for nome, vazio in DADOS_VAZIOS.items():
        with open(os.path.join(dest, 'dados', nome), 'w', encoding='utf-8') as f:
            json.dump(vazio, f, ensure_ascii=False, indent=1)
            f.write('\n')
    for pasta in ('postagens', 'pinterest', 'img/cards', 'ofertas', 'lojas'):
        os.makedirs(os.path.join(dest, pasta), exist_ok=True)


def claude_md(dest, m):
    modelo = open(os.path.join(RAIZ, 'modelo', 'CLAUDE.modelo.md'), encoding='utf-8').read()
    campos = dict(m)
    campos.setdefault('telegram_canal', m['instagram'])
    campos.setdefault('telegram_bot', m['prefixo'] + '_bot')
    campos.setdefault('awin_publisher', '(ainda não tem)')
    campos.setdefault('shopee_afiliado', '(ainda não tem)')
    campos.setdefault('dono', 'o dono da marca')
    for k, v in campos.items():
        modelo = modelo.replace('{{' + k + '}}', str(v))
    open(os.path.join(dest, 'CLAUDE.md'), 'w', encoding='utf-8').write(modelo)
    for doc in ('ESTRUTURA.md', 'REPLICAR.md'):
        shutil.copy2(os.path.join(RAIZ, 'modelo', doc), os.path.join(dest, doc))


def vestigios(dest):
    achados = []
    # "binga"/"achadinhos" sozinhos (não dentro de outra palavra, para não pegar o prefixo da marca nova)
    padrao = re.compile(r'\bachadinhos\b|\bbinga\b|\bherlison\w*\b|3147693|18306050983', re.I)
    for raiz, pastas, arqs in os.walk(dest):
        pastas[:] = [x for x in pastas if x not in IGNORAR and x != 'fonts']
        for a in arqs:
            # CLAUDE.md cita a origem de propósito (linhagem); ESTRUTURA/REPLICAR são deste modelo
            if a in ('ESTRUTURA.md', 'REPLICAR.md', 'CLAUDE.md') or os.path.splitext(a)[1] not in TEXTO:
                continue
            p = os.path.join(raiz, a)
            try:
                for i, linha in enumerate(open(p, encoding='utf-8'), 1):
                    if padrao.search(linha):
                        achados.append('%s:%d: %s' % (os.path.relpath(p, dest), i, linha.strip()[:120]))
            except UnicodeDecodeError:
                pass
    return achados


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('marca', help='arquivo JSON da marca (veja modelo/marca.exemplo.json)')
    ap.add_argument('destino', help='pasta nova (fora deste repositório)')
    ap.add_argument('--sobrescrever', action='store_true')
    a = ap.parse_args()

    m = json.load(open(a.marca, encoding='utf-8'))
    m.setdefault('dono', 'o dono da marca')
    falta = [k for k in OBRIGATORIOS if not m.get(k)]
    if falta:
        sys.exit('Faltam no marca.json: ' + ', '.join(falta))
    if not re.fullmatch(r'[a-z][a-z0-9]{2,20}', m['prefixo']):
        sys.exit('prefixo: só letras minúsculas e números, 3 a 21 caracteres (ex.: "garimpo")')
    for k in ('token', 'senha', 'secret', 'key', 'chave'):
        if any(k in c.lower() for c in m):
            sys.exit('O marca.json não pode ter segredo (%s). Segredos vão no GitHub Secrets/Cloudflare.' % k)

    dest = os.path.abspath(a.destino)
    if dest.startswith(RAIZ + os.sep) or dest == RAIZ:
        sys.exit('Escolha uma pasta FORA deste repositório.')
    if os.path.exists(dest) and os.listdir(dest) and not a.sobrescrever:
        sys.exit('A pasta já existe e não está vazia (use --sobrescrever).')

    copiar(dest)
    n = trocar(dest, substituicoes(m))
    esvaziar_site(dest)
    zerar_dados(dest)
    claude_md(dest, m)
    resto = vestigios(dest)
    print('Marca "%s" criada em %s' % (m['nome'], dest))
    print('Arquivos adaptados: %d' % n)
    if resto:
        print('ATENÇÃO, %d linha(s) ainda citam o Achadinhos (revise):' % len(resto))
        for r in resto[:40]:
            print('  ' + r)
    else:
        print('Nenhum vestígio do Achadinhos no código.')
    print('Próximo passo: siga REPLICAR.md na pasta nova (logo, cores, contas, segredos, Workers).')


if __name__ == '__main__':
    main()

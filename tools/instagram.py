#!/usr/bin/env python3
"""Publicador do Instagram (API oficial "Instagram API with Instagram Login") para o @achadinhosdobinga.

Roda no GitHub Actions. Lê a fila em dados/posts.json: publica os posts com canal "ig", status "agendado",
formato "carrossel" ou "post" (reel não), cuja data+hora (horário de Brasília) já passou.

Cada post agendado precisa de:
  "imagens": ["postagens/<id>/01.jpg", ...]   JPEG (a API do Instagram não aceita PNG), 2 a 10 para carrossel, 1 para post
  "legenda": "texto completo da legenda"
  "produtos": [ids de dados/itens.json]       usados na trava de preço

Travas (se falhar, o post vira "bloqueado" e o Telegram avisa; nada é publicado):
  - todo produto existe em itens.json, foi conferido há no máximo 7 dias (campo "max_idade_dias" muda isso)
    e o preço atual aparece escrito na legenda como "R$ 52,82";
  - o horário não passou há mais de 6 horas (preço velho não vai ao ar);
  - todas as imagens abrem publicamente e são JPEG;
  - o mesmo texto não foi publicado nas últimas 24 h (evita duplicar se uma execução anterior falhou no meio).

Variáveis de ambiente (segredos do GitHub, nunca no repositório): IG_TOKEN, IG_USER_ID.
Opcionais: TELEGRAM_TOKEN, TELEGRAM_CHAT (avisos).

Comandos:
  python3 tools/instagram.py testar            valida a fila e as travas, sem publicar nem chamar a API
  python3 tools/instagram.py publicar          publica o que estiver no horário
  python3 tools/instagram.py status            confere o token (usuário) e renova o prazo de 60 dias
"""
import json, os, sys, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
POSTS = RAIZ / "dados" / "posts.json"
ITENS = RAIZ / "dados" / "itens.json"
GRAPH = "https://graph.instagram.com/v21.0"
RAW = "https://raw.githubusercontent.com/herlison14/achadinhos/main/"
BRT = timezone(timedelta(hours=-3))
ATRASO_MAX_H = 6
IDADE_MAX_DIAS = 7


def ler(p, padrao):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return padrao


def gravar(p, obj):
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")


def avisar(texto):
    tok, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT")
    print("AVISO:", texto)
    if not tok or not chat:
        return
    try:
        dados = urllib.parse.urlencode({"chat_id": chat, "text": "Instagram: " + texto}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", dados, timeout=30)
    except Exception as e:  # aviso é só um extra
        print("(aviso ao Telegram falhou:", type(e).__name__, ")")


# ---------- API ----------
class ErroAPI(Exception):
    pass


def api(metodo, caminho, dados=None):
    """Chama a API. O token vai no corpo/parâmetro e nunca é impresso."""
    tok = os.environ.get("IG_TOKEN", "")
    dados = dict(dados or {})
    dados["access_token"] = tok
    corpo = urllib.parse.urlencode(dados)
    try:
        if metodo == "GET":
            r = urllib.request.urlopen(f"{GRAPH}{caminho}?{corpo}", timeout=60)
        else:
            r = urllib.request.urlopen(urllib.request.Request(f"{GRAPH}{caminho}", corpo.encode(), method="POST"), timeout=120)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read()).get("error", {}).get("message", "")
        except Exception:
            msg = ""
        raise ErroAPI("HTTP %d %s" % (e.code, msg.replace(tok, "***") if tok else msg))


def esperar_pronto(container, tentativas=30):
    for _ in range(tentativas):
        s = api("GET", "/" + container, {"fields": "status_code"}).get("status_code")
        if s == "FINISHED":
            return
        if s in ("ERROR", "EXPIRED"):
            raise ErroAPI("contêiner %s ficou %s" % (container, s))
        time.sleep(4)
    raise ErroAPI("contêiner %s não terminou a tempo" % container)


# ---------- travas ----------
def imagem_publica_jpeg(url):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "achadinhos-publicador"}), timeout=30)
        ct = r.headers.get("Content-Type", "")
        cab = r.read(4)
        return ct.startswith("image/jpeg") and cab[:2] == b"\xff\xd8", ct
    except Exception as e:
        return False, type(e).__name__


def validar(post, itens, agora, checar_rede):
    """Devolve lista de problemas (vazia = pode publicar)."""
    erros = []
    imgs, leg = post.get("imagens") or [], (post.get("legenda") or "").strip()
    car = post.get("formato") == "carrossel"
    if not leg:
        erros.append("sem legenda")
    if len(leg) > 2200:
        erros.append("legenda com mais de 2200 caracteres")
    if car and not 2 <= len(imgs) <= 10:
        erros.append("carrossel precisa de 2 a 10 imagens")
    if not car and len(imgs) != 1:
        erros.append("post simples precisa de 1 imagem")
    for i in imgs:
        if not i.lower().endswith((".jpg", ".jpeg")):
            erros.append("imagem não é JPEG: " + i)
        elif not (RAIZ / i).exists():
            erros.append("imagem não existe no repositório: " + i)
    if "Publicidade" not in leg:
        erros.append('legenda sem o aviso "Publicidade: links de afiliado"')
    if not post.get("produtos"):
        erros.append("sem produtos para a trava de preço")
    maxd = int(post.get("max_idade_dias", IDADE_MAX_DIAS))
    for pid in post.get("produtos", []):
        it = itens.get(pid)
        if not it:
            erros.append("produto desconhecido: " + pid)
            continue
        idade = (agora.date() - datetime.fromisoformat(it["conferido"]).date()).days
        if idade > maxd:
            erros.append("preço de %s conferido há %d dias (máximo %d)" % (pid, idade, maxd))
        if "R$ " + it["preco"] not in leg:
            erros.append("a legenda não traz o preço atual R$ %s de %s" % (it["preco"], pid))
    if checar_rede and not erros:
        for i in imgs:
            ok, ct = imagem_publica_jpeg(RAW + i)
            if not ok:
                erros.append("imagem não abre como JPEG público (%s): %s" % (ct, i))
    return erros


def horario(post):
    h = post.get("hora") or "12:00"
    return datetime.fromisoformat(post["data"] + "T" + h + ":00").replace(tzinfo=BRT)


def ja_publicado(post, ig_id):
    """Procura a mesma legenda nas últimas publicações (proteção contra duplicar)."""
    try:
        recentes = api("GET", "/%s/media" % ig_id, {"fields": "caption,timestamp,id", "limit": "15"}).get("data", [])
    except ErroAPI as e:
        print("não consegui listar publicações recentes:", e)
        return None
    primeira = (post.get("legenda") or "").strip().splitlines()[0]
    for m in recentes:
        if (m.get("caption") or "").strip().startswith(primeira):
            return m["id"]
    return None


def publicar_post(post, ig_id):
    imgs = [RAW + i for i in post["imagens"]]
    leg = post["legenda"].strip()
    if post["formato"] == "carrossel":
        filhos = []
        for u in imgs:
            c = api("POST", "/%s/media" % ig_id, {"image_url": u, "is_carousel_item": "true"})["id"]
            esperar_pronto(c)
            filhos.append(c)
        cont = api("POST", "/%s/media" % ig_id, {"media_type": "CAROUSEL", "children": ",".join(filhos), "caption": leg})["id"]
    else:
        cont = api("POST", "/%s/media" % ig_id, {"image_url": imgs[0], "caption": leg})["id"]
    esperar_pronto(cont)
    return api("POST", "/%s/media_publish" % ig_id, {"creation_id": cont})["id"]


def cmd_publicar(testar=False):
    posts = ler(POSTS, [])
    itens = {i["id"]: i for i in ler(ITENS, [])}
    agora = datetime.now(BRT)
    ig_id = os.environ.get("IG_USER_ID", "")
    if not testar and (not os.environ.get("IG_TOKEN") or not ig_id):
        # Sem as chaves o robô nunca publica. Antes saía em silêncio; agora avisa e falha (execução vermelha no GitHub).
        vencidos = [p["id"] for p in posts if p.get("canal") == "ig" and p.get("status") == "agendado"
                    and p.get("formato") in ("carrossel", "post") and (agora - horario(p)).total_seconds() >= 0]
        if vencidos:
            avisar("IG_TOKEN/IG_USER_ID não estão configurados no GitHub (Settings > Secrets > Actions): "
                   "nada foi publicado. Pendentes no horário: " + ", ".join(vencidos[:5]))
            return 3
        print("IG_TOKEN/IG_USER_ID não configurados e nenhum post no horário: nada a fazer.")
        return 0
    mudou = False
    for p in posts:
        ativo = p.get("status") == "agendado" or (testar and p.get("status") == "planejado" and p.get("imagens"))
        if p.get("canal") != "ig" or not ativo or p.get("formato") not in ("carrossel", "post"):
            continue
        quando = horario(p)
        atraso_h = (agora - quando).total_seconds() / 3600
        erros = validar(p, itens, agora, checar_rede=not testar)
        if testar:
            print("%-28s %s  %s" % (p["id"], quando.strftime("%d/%m/%Y %H:%M"), "OK" if not erros else "PROBLEMAS: " + "; ".join(erros)))
            continue
        if atraso_h < 0:
            continue
        if atraso_h > ATRASO_MAX_H:
            erros.append("passou do horário há %.0f h; confira os preços e reagende" % atraso_h)
        if erros:
            p["status"], p["nota"] = "bloqueado", "; ".join(erros)[:400]
            mudou = True
            avisar("post %s NÃO foi publicado: %s" % (p["id"], p["nota"]))
            continue
        existente = ja_publicado(p, ig_id)
        if existente:
            p["status"], p["ig_id"], p["nota"] = "publicado", existente, "já estava no perfil (não duplicou)"
            mudou = True
            continue
        try:
            mid = publicar_post(p, ig_id)
            p["status"], p["ig_id"] = "publicado", mid
            p["publicado_em"] = datetime.now(BRT).strftime("%Y-%m-%d %H:%M")
            mudou = True
            avisar("post %s publicado no Instagram." % p["id"])
        except ErroAPI as e:
            p["status"], p["nota"] = "erro", str(e)[:300]
            mudou = True
            avisar("erro ao publicar %s: %s" % (p["id"], e))
    if mudou:
        gravar(POSTS, posts)
    return 0


def cmd_status():
    if not os.environ.get("IG_TOKEN") or not os.environ.get("IG_USER_ID"):
        avisar("IG_TOKEN/IG_USER_ID não estão configurados no GitHub (Settings > Secrets > Actions).")
        return 3
    try:
        eu = api("GET", "/me", {"fields": "user_id,username"})
        print("Conta:", eu.get("username"), "| id:", eu.get("user_id"))
        r = urllib.request.urlopen(f"{GRAPH}/refresh_access_token?" + urllib.parse.urlencode(
            {"grant_type": "ig_refresh_token", "access_token": os.environ["IG_TOKEN"]}), timeout=30)
        dados = json.loads(r.read())
        dias = int(dados.get("expires_in", 0)) // 86400
        print("Token renovado; vale por mais ~%d dias." % dias)
        if dados.get("access_token") and dados["access_token"] != os.environ["IG_TOKEN"]:
            avisar("a renovação gerou um token DIFERENTE: gere um novo no painel da Meta e troque o segredo IG_TOKEN.")
    except (ErroAPI, urllib.error.URLError, urllib.error.HTTPError) as e:
        det = str(e) if isinstance(e, ErroAPI) else type(e).__name__
        print("::error::Instagram recusou o token: " + det[:200].replace("\n", " "))  # ErroAPI já vem sem o token
        avisar("token do Instagram com problema (%s). Gere um novo e troque o segredo IG_TOKEN." % type(e).__name__)
        return 1
    return 0


if __name__ == "__main__":
    # tira espaços, quebras de linha e aspas que costumam vir junto ao colar o segredo no GitHub
    for _k in ("IG_TOKEN", "IG_USER_ID"):
        if os.environ.get(_k):
            os.environ[_k] = "".join(os.environ[_k].split()).strip("\"'")
    c = sys.argv[1] if len(sys.argv) > 1 else "testar"
    sys.exit({"testar": lambda: cmd_publicar(True), "publicar": cmd_publicar, "status": cmd_status}.get(c, lambda: sys.exit(__doc__))())

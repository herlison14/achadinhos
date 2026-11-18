#!/data/data/com.termux/files/usr/bin/bash
# Instala o conferidor de preços no celular (Termux). Pode rodar de novo sem estragar nada.
#   pkg update -y && pkg install -y git
#   git clone https://github.com/herlison14/achadinhos ~/achadinhos && bash ~/achadinhos/tools/instalar_celular.sh
set -e
REPO="$HOME/achadinhos"
echo "== 1/5 Pacotes"; pkg update -y; pkg install -y python git gh cronie termux-services
echo "== 2/5 Repositório"
[ -d "$REPO/.git" ] || git clone https://github.com/herlison14/achadinhos "$REPO"
cd "$REPO"; git pull --rebase --autostash
echo "== 3/5 Login no GitHub (você digita o código no navegador; a chave fica só neste celular)"
gh auth status >/dev/null 2>&1 || gh auth login -p https -h github.com -w
gh auth setup-git
git config user.name  "Achadinhos (celular)"
git config user.email "herlison14@users.noreply.github.com"
echo "== 4/5 Agenda diária (10h): só liga com --agendar, depois que o teste for validado"
termux-wake-lock || true
if [ "$1" = "--agendar" ]; then
  sv-enable crond 2>/dev/null || true
  LINHA="0 10 * * * cd $REPO && termux-wake-lock && python3 -I tools/conferidor_celular.py --aplicar --limite 120 >> $HOME/conferidor.log 2>&1"
  ( crontab -l 2>/dev/null | grep -v conferidor_celular; echo "$LINHA" ) | crontab -
  echo "Agendado: todo dia às 10h."
else
  echo "Não agendado (modo teste). Para ligar depois: bash ~/achadinhos/tools/instalar_celular.sh --agendar"
fi
echo "== 5/5 Teste (não grava nada)"
[ "$1" = "--agendar" ] || python3 -I tools/conferidor_celular.py --limite 150
echo; echo "Pronto. Mande o 'Resumo por loja' acima para o Claude. O teste salva a CALIBRAÇÃO: sem ele o --aplicar se recusa a rodar."

#!/usr/bin/env bash
# spark-health — kontrola dostępności Sparka i usług z Maca (tylko odczyt).
#
# Sprawdza po kolei: nazwę w sieci (mDNS) → SSH → tunel na Macu (porty 8000–8004, 8080)
# → usługi przez tunel (/health, nazwa modelu z /v1/models) → stan kontenerów, pamięć i czas
# działania Sparka. Na końcu podpowiedź, co naprawić.
#
# Użycie: scripts/spark-health.sh        (alias SSH „spark” z ssh/config.example)
# Zależności: bash (także 3.2 z macOS), ssh, curl, nc, lsof.

set -u
HOST="spark-28e3.local"
PORTS="8000 8001 8002 8003 8004 8080"
SSH="ssh -o ClearAllForwardings=yes -o BatchMode=yes -o ConnectTimeout=6 spark"
ok()   { printf '  \033[32mOK\033[0m   %s\n' "$1"; }
bad()  { printf '  \033[31mBŁĄD\033[0m %s\n' "$1"; }
info() { printf '  ·    %s\n' "$1"; }
fix=""

echo "Spark ($HOST) — $(date '+%F %T')"

echo "Sieć"
if ping -c 1 -t 3 "$HOST" >/dev/null 2>&1; then ok "ping $HOST"
else bad "brak odpowiedzi na ping — Mac w innej sieci albo Spark wyłączony"; fix="$fix\n- sprawdź sieć Maca (ta sama co Spark) i zasilanie Sparka"; fi

echo "SSH"
if remote=$($SSH 'echo "działa $(uptime -p | sed "s/^up //") (od $(uptime -s))"; free -h | awk "/Mem:/{print \"pamięć: \"\$3\" użyte, \"\$7\" dostępne z \"\$2}"; docker ps -a --format "{{.Names}}\t{{.Status}}"' 2>/dev/null); then
  ok "logowanie przez klucz"
  echo "$remote" | sed -n '1,2p' | while read -r l; do info "$l"; done
  echo "Kontenery"
  echo "$remote" | sed -n '3,$p' | while IFS=$'\t' read -r n st; do
    case "$st" in *healthy*|*"Up "*) case "$st" in *unhealthy*) bad "$n — $st";; *) ok "$n — $st";; esac;;
      *) bad "$n — $st";; esac; done
  [ -z "$(echo "$remote" | sed -n '3,$p')" ] && { info "brak kontenerów (make down?)"; fix="$fix\n- na Sparku: cd ~/spark-setup && make up SET=<zestaw> (w tmux)"; }
else
  bad "SSH nie działa"; fix="$fix\n- ssh spark (klucz w agencie? ssh-add -l)"
fi

echo "Tunel i usługi (z Maca)"
tunnel=0
for p in $PORTS; do
  if lsof -nP -iTCP:"$p" -sTCP:LISTEN 2>/dev/null | grep -q '^ssh'; then
    tunnel=1
    if [ "$p" = 8080 ]; then code=$(curl -s -m 4 -o /dev/null -w '%{http_code}' "localhost:$p/health"); name="Open WebUI"
    else code=$(curl -s -m 4 -o /dev/null -w '%{http_code}' "localhost:$p/health")
      name=$(curl -s -m 4 "localhost:$p/v1/models" | grep -o '"id": *"[^"]*"' | head -1 | sed -E 's/.*"([^"]*)"$/\1/'); fi
    if [ "$code" = 200 ]; then ok ":$p ${name:-?}"
    else info ":$p tunel jest, usługa nie odpowiada (HTTP $code) — model nie działa w tym zestawie"; fi
  else
    who=$(lsof -nP -iTCP:"$p" -sTCP:LISTEN 2>/dev/null | awk 'NR==2{print $1}')
    [ -n "$who" ] && bad ":$p zajęty na Macu przez „$who” — tunel się nie zestawi (ExitOnForwardFailure)" || info ":$p brak tunelu"
  fi
done
[ $tunnel = 0 ] && { bad "brak tunelu SSH"; fix="$fix\n- uruchom tunel: ssh -N spark (po uśpieniu Maca albo zmianie sieci tunel się kończy)"; }

if [ -n "$fix" ]; then printf '\nDo naprawy:%b\n' "$fix"; else echo; echo "Wszystko działa."; fi

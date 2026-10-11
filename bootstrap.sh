#!/usr/bin/env bash
# Przygotowanie DGX Spark po instalacji / resecie fabrycznym.
# Idempotentny: można uruchamiać wielokrotnie.
#
#   sudo ./bootstrap.sh michal                # pakiety, konto, grupy, /data, klucze SSH
#   sudo ./bootstrap.sh --harden-ssh michal   # dodatkowo: tylko klucze, tylko ten użytkownik
#
# Klucze publiczne: ssh/authorized_keys (jeden na linię; klucze publiczne mogą być w gicie).
set -euo pipefail

HARDEN_SSH=0
if [[ "${1:-}" == "--harden-ssh" ]]; then HARDEN_SSH=1; shift; fi
TARGET_USER="${1:-${SUDO_USER:-}}"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LLM_GROUP=llm
DATA_DIR=/data
HF_DIR=$DATA_DIR/hf
VOL_DIR=$DATA_DIR/volumes
TIMEZONE=Europe/Warsaw
PACKAGES=(git make curl jq htop nvtop tmux python3-yaml avahi-daemon)

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }

[[ $EUID -eq 0 ]] || { echo "Uruchom przez sudo"; exit 1; }
[[ -n "$TARGET_USER" ]] || { echo "Podaj nazwę użytkownika: sudo ./bootstrap.sh <user>"; exit 1; }

log "Strefa czasowa: $TIMEZONE"
timedatectl set-timezone "$TIMEZONE"

log "Pakiety: ${PACKAGES[*]}"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${PACKAGES[@]}" >/dev/null
systemctl enable --now avahi-daemon >/dev/null   # nazwa <hostname>.local w sieci (mDNS)

log "Grupa $LLM_GROUP"
getent group "$LLM_GROUP" >/dev/null || groupadd "$LLM_GROUP"

log "Użytkownik $TARGET_USER"
if ! id "$TARGET_USER" &>/dev/null; then
  adduser --disabled-password --gecos "" "$TARGET_USER"
  warn "Konto utworzone bez hasła. Ustaw je: sudo passwd $TARGET_USER (sudo go wymaga)"
fi
usermod -aG sudo,docker,"$LLM_GROUP" "$TARGET_USER"

# Pozostali członkowie zespołu z dostępem do modeli: dopisz tutaj.
for u in dai-coe; do
  id "$u" &>/dev/null && usermod -aG "$LLM_GROUP" "$u" || true
done

log "Katalogi danych: $HF_DIR, $VOL_DIR"
mkdir -p "$HF_DIR" "$VOL_DIR"
chown root:"$LLM_GROUP" "$HF_DIR" "$VOL_DIR"
chmod 2775 "$HF_DIR" "$VOL_DIR"   # setgid: nowe pliki dziedziczą grupę llm

KEYS_FILE="$REPO_DIR/ssh/authorized_keys"
HOME_DIR="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
if [[ -s "$KEYS_FILE" ]]; then
  log "Klucze SSH z ssh/authorized_keys -> $HOME_DIR/.ssh/authorized_keys"
  install -d -m 700 -o "$TARGET_USER" -g "$TARGET_USER" "$HOME_DIR/.ssh"
  touch "$HOME_DIR/.ssh/authorized_keys"
  while IFS= read -r key; do
    [[ -z "$key" || "$key" == \#* ]] && continue
    grep -qxF "$key" "$HOME_DIR/.ssh/authorized_keys" || echo "$key" >> "$HOME_DIR/.ssh/authorized_keys"
  done < "$KEYS_FILE"
  chown "$TARGET_USER:$TARGET_USER" "$HOME_DIR/.ssh/authorized_keys"
  chmod 600 "$HOME_DIR/.ssh/authorized_keys"
else
  warn "Brak ssh/authorized_keys — klucz skopiuj z Maca: ssh-copy-id spark"
fi

if [[ $HARDEN_SSH -eq 1 ]]; then
  if [[ ! -s "$HOME_DIR/.ssh/authorized_keys" ]]; then
    warn "Pomijam --harden-ssh: $TARGET_USER nie ma żadnego klucza (odcięłoby to dostęp)"
  else
    log "SSH: tylko klucze, bez roota, tylko $TARGET_USER"
    cat > /etc/ssh/sshd_config.d/10-spark.conf <<EOF
# Zarządzane przez spark-setup/bootstrap.sh
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
AllowUsers $TARGET_USER
EOF
    sshd -t
    systemctl reload ssh
    warn "Nie zamykaj obecnej sesji, dopóki nie sprawdzisz w NOWYM terminalu: ssh spark"
  fi
fi

log "Test: Docker + GPU"
if docker run --rm --gpus all ubuntu nvidia-smi -L; then
  log "GPU widoczne w kontenerach"
else
  warn "Kontener nie widzi GPU — sprawdź NVIDIA Container Toolkit"
fi

cat <<EOF

Gotowe. Dalej (jako $TARGET_USER, po ponownym zalogowaniu — nowe grupy działają w nowej sesji):
  cp .env.example .env && chmod 600 .env   # uzupełnij HF_TOKEN
  make models SET=c
  make up SET=c
  make test
EOF

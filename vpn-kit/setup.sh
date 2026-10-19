#!/usr/bin/env bash
# ============================================================
#  VPN-KIT — свой VPN на VPS в Европе (для России, 2026)
#
#  Вариант 1: свой домен  -> VLESS Reality (self-steal) + Hysteria2
#  Вариант 2: без домена  -> Hysteria2
#
#  Запускать на НОВОМ VPS (Ubuntu 22.04/24.04 или Debian 12)
#  от root, одной строкой (URL гиста смотри в README):
#    bash <(curl -fsSL https://gist.githubusercontent.com/.../raw)
# ============================================================
set -uo pipefail

red()    { printf '\033[31m%s\n\033[0m' "$*"; }
green()  { printf '\033[32m%s\n\033[0m' "$*"; }
yellow() { printf '\033[33m%s\n\033[0m' "$*"; }
info()   { printf '\n\033[36m==>\033[0m %s\n' "$*"; }
die()    { red "❌ $*"; exit 1; }

[[ ${EUID} -eq 0 ]] || die "Запусти от root (или добавь sudo в начало команды)."

# ---------- проверка системы ---------------------------------
OS_ID="unknown"
if [[ -r /etc/os-release ]]; then
  OS_ID="$(. /etc/os-release && echo "${ID:-unknown}")"
fi
case "$OS_ID" in
  ubuntu|debian) : ;;
  *) die "Я умею только на Ubuntu 22.04/24.04 или Debian 12. Твоя система: $OS_ID" ;;
esac
green "✅ Система: $OS_ID — понимаю."

# ---------- интернет / IP сервера -----------------------------
info "Проверяю интернет на сервере…"
PUBLIC_IP="$(curl -s4 --max-time 15 https://ifconfig.me || true)"
[[ -n "${PUBLIC_IP:-}" ]] || die "У сервера нет интернета. Проверь хостинг."
info "IP сервера: $PUBLIC_IP"

export DEBIAN_FRONTEND=noninteractive
info "Ставлю базовые пакеты (apt, может занять минуту)…"
apt-get update -qq || die "Не обновил apt. Проверь интернет/фаервол хостера."
apt-get install -y -qq curl ca-certificates openssl dnsutils >/dev/null

# ---------- меню ---------------------------------------------
echo
echo "  Что есть для VPN?"
echo "   1) Свой домен (например, mysite.com) — ЛУЧШИЙ вариант."
echo "      (VLESS Reality будет прятаться за твоим же сайтом —"
echo "       самое трудное для блокировщиков)"
echo "   2) Домена нет — поставлю Hysteria2 (быстро, без домена)"
echo
read -rp "Введи 1 или 2 и нажми Enter: " CHOICE
CHOICE="${CHOICE// /}"
[[ "$CHOICE" =~ ^[12]$ ]] || die "Не понял ответ. Запусти скрипт заново и введи 1 или 2."

CRED=/root/vpn-credentials.txt
VLESS_LINK=""
HY_LINK=""
DOMAIN=""

# ---------- Hysteria2 (запасной вариант) ----------------------
install_hysteria() {
  local cn="$1"
  info "Ставлю Hysteria2 (запасной вариант)…"
  if ! command -v hysteria >/dev/null 2>&1; then
    curl -fsSL https://get.hy2.sh/ | bash || die "Не смог поставить Hysteria2."
  fi
  # гасим стоковый сервис, если инсталлятор его создал
  systemctl stop hysteria 2>/dev/null || true
  systemctl disable hysteria 2>/dev/null || true

  mkdir -p /usr/local/etc/hysteria
  if [[ ! -f /usr/local/etc/hysteria/key.pem ]]; then
    openssl ecparam -name prime256v1 -genkey -noout -out /usr/local/etc/hysteria/key.pem
    openssl req -x509 -noenc -key /usr/local/etc/hysteria/key.pem -days 3650 \
      -out /usr/local/etc/hysteria/cert.pem -subj "/CN=$cn"
  fi
  local huser hpass
  huser="user"
  hpass="$(openssl rand -base64 18 | tr -d '=+/' | cut -c1-22)"
  cat > /usr/local/etc/hysteria/config.yaml <<EOF
listen: :443
tls:
  cert: /usr/local/etc/hysteria/cert.pem
  key: /usr/local/etc/hysteria/key.pem
auth:
  type: password
  password: "$hpass"
EOF
  cat > /etc/systemd/system/hysteria2.service <<'EOF'
[Unit]
Description=Hysteria2 (VPN-KIT)
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/local/bin/hysteria server -c /usr/local/etc/hysteria/config.yaml
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable --now hysteria2
  HY_LINK="hysteria2://$huser:$hpass@$PUBLIC_IP:443/?insecure=1"
  if systemctl is-active --quiet hysteria2; then
    green "✅ Hysteria2 запущена (порт 443, UDP)."
  else
    yellow "Хм, Hysteria2 не стартовала. Посмотри: systemctl status hysteria2"
  fi
}

# ---------- вариант 1: свой домен (self-steal) ----------------
if [[ "$CHOICE" == "1" ]]; then
  echo
  read -rp "Твой домен (например, example.com или blog.example.com): " DOMAIN
  DOMAIN="$(echo "$DOMAIN" | tr '[:upper:]' '[:lower:]' | sed -e 's#^https\?://##' -e 's#/*$##' -e 's#^/##')"
  [[ -n "$DOMAIN" ]] || die "Домен пустой."
  if ! [[ "$DOMAIN" =~ ^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$ ]]; then
    die "Похоже, это не домен: $DOMAIN
    (Если домен с кириллицей — у регистратора в DNS-настройках показана латиница вида xn--..., введи её)"
  fi

  info "Проверяю, что домен $DOMAIN указывает на $PUBLIC_IP (A-запись)…"
  attempt=0
  while :; do
    RESOLVED="$(dig +short "$DOMAIN" A 2>/dev/null | grep -E '^[0-9]{1,3}(\.[0-9]{1,3}){3}$' | tail -n1 || true)"
    if [[ "${RESOLVED:-}" == "$PUBLIC_IP" ]]; then
      green "✅ DNS в порядке: $DOMAIN → $PUBLIC_IP"
      break
    fi
    attempt=$((attempt+1))
    if [[ $attempt -ge 4 ]]; then
      die "Домен всё ещё указывает на ${RESOLVED:-<никуда>}.
      Загляни к регистратору и поставь A-запись: имя = $DOMAIN, значение = $PUBLIC_IP, TTL = 60,
      проксирование/CDN (оранжевое облако) — ВЫКЛ. Подожди 5–30 минут и запусти скрипт снова."
    fi
    yellow "Сейчас: $DOMAIN → ${RESOLVED:-<никуда>} (а нужно $PUBLIC_IP)"
    echo "   Задай у регистратора A-запись: $DOMAIN = $PUBLIC_IP (без CDN)."
    echo "   Когда сделаешь — нажми Enter, я проверю снова (попытка $attempt/3)…"
    read -rp "" _
    sleep 15
  done

  info "Ставлю nginx и certbot…"
  apt-get install -y -qq nginx certbot >/dev/null

  read -rp "Email для сертификата (Let's Encrypt пришлёт на него письма о продлении; подойдёт любой): " EMAIL
  if ! [[ "$EMAIL" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
    die "Похоже, это не email: $EMAIL"
  fi

  info "Получаю бесплатный сертификат Let's Encrypt для $DOMAIN…"
  certbot certonly --webroot -w /var/www/html -d "$DOMAIN" \
    --non-interactive --agree-tos -m "$EMAIL" \
    --deploy-hook "systemctl reload nginx" \
    || die "Let's Encrypt не выдал сертификат. Обычно значит, что A-запись ещё не прогрузилась — подожди 10 минут и запусти скрипт снова."

  info "Настраиваю nginx (сайт уезжает на 127.0.0.1:8443, порт 443 отдам Xray)…"
  rm -f /etc/nginx/sites-enabled/default
  cat > /etc/nginx/sites-available/selfsite <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 127.0.0.1:8443 ssl;
    server_name $DOMAIN;

    ssl_certificate     /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    root /var/www/selfsite;
    index index.html;
}
EOF
  mkdir -p /var/www/selfsite
  cat > /var/www/selfsite/index.html <<'EOF'
<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><title>Мой сайт</title>
<style>body{font-family:system-ui,sans-serif;display:grid;place-items:center;height:100vh;margin:0;background:#0b1220;color:#dbe3f0}</style>
</head><body><div style="text-align:center">
<h1>Работает 🚀</h1>
<p>Обычный сайт на своём сервере. Ничего подозрительного.</p>
</div></body></html>
EOF
  ln -sf /etc/nginx/sites-available/selfsite /etc/nginx/sites-enabled/selfsite
  nginx -t >/dev/null 2>&1 || die "Конфиг nginx не прошёл проверку. Запусти скрипт ещё раз."
  systemctl reload nginx

  info "Ставлю Xray (сам VLESS-сервер)…"
  if ! command -v xray >/dev/null 2>&1; then
    bash -c "$(curl -Ls https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install \
      || die "Не смог поставить Xray."
  fi

  info "Генерирую ключи и UUID…"
  UUID="$(xray uuid)"
  KV="$(xray x25519)"
  PRIV="$(printf '%s\n' "$KV" | grep -i 'private key' | awk '{print $NF}')"
  PUB="$(printf '%s\n' "$KV" | grep -iE 'public ?key' | grep -vi 'private' | awk '{print $NF}')"
  SID="$(openssl rand -hex 8)"
  [[ -n "${UUID:-}" && -n "${PRIV:-}" && -n "${PUB:-}" && -n "${SID:-}" ]] \
    || die "Не смог сгенерировать ключи. Запусти скрипт ещё раз."

  if [[ -f /usr/local/etc/xray/config.json ]]; then
    cp /usr/local/etc/xray/config.json "/usr/local/etc/xray/config.json.bak.$(date +%s)"
    yellow "Сохранил бэкап существующего конфига Xray (старые VPN-ссылки перестанут работать)."
  fi
  mkdir -p /usr/local/etc/xray
  cat > /usr/local/etc/xray/config.json <<EOF
{
  "log": { "loglevel": "warning" },
  "inbounds": [
    {
      "listen": "0.0.0.0",
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [ { "id": "$UUID", "flow": "xtls-rprx-vision" } ],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "target": "127.0.0.1:8443",
          "serverNames": [ "$DOMAIN" ],
          "privateKey": "$PRIV",
          "shortIds": [ "$SID" ]
        }
      },
      "sniffing": { "enabled": true, "destOverride": [ "http", "tls", "quic" ] }
    }
  ],
  "outbounds": [
    { "protocol": "freedom", "tag": "direct" },
    { "protocol": "blackhole", "tag": "block" }
  ]
}
EOF
  xray run -test -c /usr/local/etc/xray/config.json || die "Конфиг Xray не прошёл проверку."
  systemctl enable --now xray
  systemctl restart xray
  sleep 2
  CODE="$(curl -skI -o /dev/null -w '%{http_code}' --max-time 10 "https://$DOMAIN" || true)"
  if [[ "$CODE" == "200" ]]; then
    green "✅ https://$DOMAIN открывается через Xray — любой, кто «посмотрит» на сервер, увидит просто твой сайт."
  else
    yellow "Хм, https://$DOMAIN вернул статус ${CODE:-«ничего»}.
    Обычно это фаервол хостера: открой в панели TCP-порт 443 и попробуй снова."
  fi

  VLESS_LINK="vless://$UUID@$DOMAIN:443?encryption=none&flow=xtls-rprx-vision&security=reality&sni=$DOMAIN&fp=chrome&pbk=$PUB&sid=$SID&type=tcp#vpn-kit"
  install_hysteria "$DOMAIN"
else
  # ---------- вариант 2: без домена ---------------------------
  echo
  info "Ок, без домена. Ставлю Hysteria2 (QUIC поверх UDP 443)…"
  install_hysteria "$PUBLIC_IP"
fi

# ---------- фаервол -------------------------------------------
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q 'Status: active'; then
  ufw allow 80/tcp  >/dev/null
  ufw allow 443/tcp >/dev/null
  ufw allow 443/udp >/dev/null
  green "✅ Фаервол (ufw) открыт: 80/tcp, 443/tcp, 443/udp."
fi

# ---------- сохраняем и показываем ----------------------------
{
  echo "VPN-KIT — сгенерировано $(date '+%d.%m.%Y %H:%M')"
  echo "IP сервера: $PUBLIC_IP"
  [[ -n "$DOMAIN" ]] && echo "Домен:      $DOMAIN"
  echo
  if [[ -n "$VLESS_LINK" ]]; then
    echo "ОСНОВНАЯ ссылка (VLESS Reality — сначала подключай её):"
    echo "$VLESS_LINK"
    echo
  fi
  if [[ -n "$HY_LINK" ]]; then
    echo "ЗАПАСНАЯ ссылка (Hysteria2 — если основная не цепляется):"
    echo "$HY_LINK"
    echo
  fi
  echo "Как подключиться: приложение Hiddify (https://hiddify.com) → кнопка «+» → вставить ссылку."
} > "$CRED"
chmod 600 "$CRED"

echo
green "============================================================"
green "🎉 ГОТОВО! VPN поднят."
green "============================================================"
echo
if [[ -n "$VLESS_LINK" ]]; then
  echo "ОСНОВНАЯ ссылка (VLESS Reality):"
  echo "  $VLESS_LINK"
  echo
fi
if [[ -n "$HY_LINK" ]]; then
  echo "ЗАПАСНАЯ ссылка (Hysteria2):"
  echo "  $HY_LINK"
  echo
fi
echo "Обе ссылки также сохранены в файл $CRED"
echo
echo "Дальше (5 минут):"
echo "  1. Ставишь приложение Hiddify: https://hiddify.com"
echo "     (телефон — App Store / Google Play, ПК — скачать с сайта)"
echo "  2. Открываешь Hiddify, жмёшь «+», вставляешь основную ссылку."
echo "  3. Если основная не подключается — пробуешь запасную."
echo
echo "Если перезапустишь скрипт позже — ключи пересоздадутся,"
echo "старые ссылки перестанут работать (покажу новые)."

#!/usr/bin/env bash
# Makes the CandorNews server recover by itself. Safe to run more than once.
#   sudo bash deploy/harden-server.sh
#
# 1. If the whole server runs out of memory, reboot within 10 s instead of
#    freezing (containers start again on boot: restart: unless-stopped).
#    Out-of-memory inside one container is handled by its mem_limit instead
#    (only that container restarts) and does not trigger a reboot.
# 2. Watchdog every 2 minutes: after 3 failed checks in a row it restarts the
#    unhealthy part (backend, database, website or HTTPS proxy).
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo bash deploy/harden-server.sh" >&2
  exit 1
fi

# --- 1. reboot instead of freezing on a system-wide out-of-memory ---
cat > /etc/sysctl.d/99-candornews.conf <<'EOF'
# CandorNews: recover automatically instead of hanging.
vm.panic_on_oom = 1
kernel.panic = 10
kernel.panic_on_oops = 1
# Prefer keeping the app in memory over aggressive swapping.
vm.swappiness = 30
EOF
sysctl --system >/dev/null
systemctl enable docker >/dev/null 2>&1 || true

# --- 2. watchdog ---
install -d -m 755 /var/lib/candornews-watchdog
cat > /usr/local/bin/candornews-watchdog <<'EOF'
#!/usr/bin/env bash
# Restart a CandorNews container after 3 failed health checks in a row.
STATE=/var/lib/candornews-watchdog
check() {   # name, command...
  local name=$1; shift
  if "$@" >/dev/null 2>&1; then
    echo 0 > "$STATE/$name"
  else
    local n=$(( $(cat "$STATE/$name" 2>/dev/null || echo 0) + 1 ))
    echo "$n" > "$STATE/$name"
    logger -t candornews-watchdog "$name check failed ($n/3)"
    if [ "$n" -ge 3 ]; then
      logger -t candornews-watchdog "restarting $name"
      docker restart "candornews-$name-1" >/dev/null 2>&1 || true
      echo 0 > "$STATE/$name"
    fi
  fi
}
check mongodb  timeout 10 docker exec candornews-mongodb-1 bash -c '</dev/tcp/127.0.0.1/27017'
check backend  timeout 15 docker exec candornews-backend-1 curl -fsS -m 10 http://localhost:8080/health
check frontend timeout 10 docker exec candornews-frontend-1 wget -q -O /dev/null http://127.0.0.1:80
check caddy    timeout 15 curl -fsS -m 10 -o /dev/null -H "Host: ${CANDORNEWS_DOMAIN:-localhost}" http://127.0.0.1/health
EOF
chmod 755 /usr/local/bin/candornews-watchdog

DOMAIN=$(grep -E '^DOMAIN=' "$(dirname "$0")/production.env" 2>/dev/null | cut -d= -f2- || true)
cat > /etc/systemd/system/candornews-watchdog.service <<EOF
[Unit]
Description=CandorNews health watchdog
After=docker.service

[Service]
Type=oneshot
Environment=CANDORNEWS_DOMAIN=${DOMAIN:-localhost}
ExecStart=/usr/local/bin/candornews-watchdog
EOF
cat > /etc/systemd/system/candornews-watchdog.timer <<'EOF'
[Unit]
Description=Run the CandorNews watchdog every 2 minutes

[Timer]
OnBootSec=3min
OnUnitActiveSec=2min

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now candornews-watchdog.timer >/dev/null

echo "Hardening applied:"
sysctl vm.panic_on_oom kernel.panic vm.swappiness
systemctl is-active candornews-watchdog.timer

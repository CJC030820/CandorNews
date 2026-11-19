#!/usr/bin/env bash
# Daily MongoDB backup for the CandorNews server. Safe to run more than once.
#   sudo bash deploy/setup-backups.sh
#
# Every day at 03:30 (Malaysia time) the whole database (accounts, articles,
# bookmarks and history) is saved as one compressed file in
# /var/backups/candornews. The newest 7 are kept.
#
# Restore a backup (replaces the current data):
#   gunzip -c /var/backups/candornews/<file>.archive.gz | \
#     docker exec -i candornews-mongodb-1 mongorestore --archive --drop
#
# Copy the latest one to your own computer (run on your computer):
#   scp -i ~/.ssh/candornews_azure azureuser@<server>:/var/backups/candornews/latest.archive.gz .
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo bash deploy/setup-backups.sh" >&2
  exit 1
fi

install -d -m 750 -o root -g "$(id -gn "${SUDO_USER:-root}")" /var/backups/candornews

cat > /usr/local/bin/candornews-backup <<'EOF'
#!/usr/bin/env bash
# Writes /var/backups/candornews/candornews-YYYY-MM-DD-HHMM.archive.gz and keeps the newest 7.
set -euo pipefail
DIR=/var/backups/candornews
KEEP=7
STAMP=$(TZ=Asia/Kuala_Lumpur date +%Y-%m-%d-%H%M)
FILE="$DIR/candornews-$STAMP.archive.gz"
TMP="$FILE.part"
# mongodump inside the database container; low priority so the site stays responsive.
nice -n 10 docker exec candornews-mongodb-1 mongodump --quiet --archive --gzip --db news_intelligence > "$TMP"
# A usable backup is never empty; keep the old ones if this one failed.
if [ ! -s "$TMP" ]; then
  rm -f "$TMP"
  echo "backup failed: empty archive" >&2
  exit 1
fi
mv "$TMP" "$FILE"
chmod 640 "$FILE"
ln -sfn "$FILE" "$DIR/latest.archive.gz"
ls -1t "$DIR"/candornews-*.archive.gz | tail -n +$((KEEP + 1)) | xargs -r rm -f
echo "backup saved: $FILE ($(du -h "$FILE" | cut -f1))"
EOF
chmod 755 /usr/local/bin/candornews-backup

cat > /etc/systemd/system/candornews-backup.service <<'EOF'
[Unit]
Description=CandorNews daily database backup
After=docker.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/candornews-backup
EOF
cat > /etc/systemd/system/candornews-backup.timer <<'EOF'
[Unit]
Description=Back up the CandorNews database every day

[Timer]
# 19:30 UTC = 03:30 Malaysia time; runs on next boot if the server was off.
OnCalendar=*-*-* 19:30:00 UTC
Persistent=true
RandomizedDelaySec=5min

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now candornews-backup.timer >/dev/null

echo "Daily backups enabled; next run:"
systemctl list-timers candornews-backup.timer --no-pager | sed -n 2p

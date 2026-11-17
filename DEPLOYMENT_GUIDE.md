# Deploying CandorNews to one server

This puts the whole system (website, API, MongoDB, news collector and email
scheduler) on one Linux server using `docker-compose.prod.yml`. Caddy serves
the site over HTTPS and is the only thing reachable from the internet.

```
Internet ──443──> Caddy ──/api, /health──> backend (FastAPI, collector, email scheduler)
                     └────────other───────> frontend (React, Nginx)
                                            backend ──> MongoDB (private)
```

**You need:** a server, a domain name pointing at it, and your Gmail App Password.
Sign-ups, payment details and passwords are entered by you.

## 1. Get a server

**Option A: Oracle Cloud Always Free (no monthly cost; a card is needed at sign-up).**

1. Create an Oracle Cloud account and choose a home region close to Malaysia (for example Singapore).
2. Create a compute instance:
   - Image: **Ubuntu 22.04 or 24.04**.
   - Shape: **VM.Standard.A1.Flex** (Ampere, Always Free eligible) with **2 OCPU and 12 GB memory**.
     Do not exceed the Always Free allowance. If the region reports "out of capacity", try again later
     or use the small AMD **VM.Standard.E2.1.Micro** shape (add swap, see step 3).
   - Add your SSH public key.
3. In the instance's **Virtual Cloud Network → Security List**, add ingress rules for TCP **80** and **443** from `0.0.0.0/0`.

**Option B: any small paid server** (about US$5/month, 1–2 GB RAM, Ubuntu). Make sure the provider
allows outgoing email on port **587**; some providers block it for new accounts.

Note the server's **public IP address**.

## 2. Get a domain name

Any of these works:

- Your own domain: add an `A` record pointing to the server IP.
- Free: [DuckDNS](https://www.duckdns.org) gives `yourname.duckdns.org`; set it to the server IP.
- Quickest: `<server-ip>.sslip.io` (for example `203.0.113.10.sslip.io`) needs no sign-up.

## 3. Prepare the server

SSH in (`ssh ubuntu@<server-ip>`), then:

```bash
sudo apt-get update && sudo apt-get -y upgrade
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

Log out and back in so the `docker` group applies.

**Oracle Ubuntu images only:** the server's own firewall blocks web traffic by default. Open it:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

**Servers with 1 GB RAM only:** add swap so the frontend can build:

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 4. Get the code and add the settings

```bash
git clone https://github.com/CJC030820/CandorNews.git
cd CandorNews
cp deploy/production.env.example deploy/production.env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # copy this for SECRET_KEY
nano deploy/production.env
```

Fill in `DOMAIN`, `SECRET_KEY`, `CORS_ORIGINS` (`https://` + your domain) and the `SMTP_*` values.
Then protect the file:

```bash
chmod 600 deploy/production.env
```

## 5. Start it

```bash
docker compose --env-file deploy/production.env -f docker-compose.prod.yml up -d --build
docker compose --env-file deploy/production.env -f docker-compose.prod.yml ps
```

The first build takes several minutes. Caddy requests the HTTPS certificate on first start.

## 6. Check it works

1. Open `https://<your-domain>`. The padlock should show and the login page should load.
2. `https://<your-domain>/health` should show `"status":"healthy"`.
3. Register an account, choose topics, and wait for the first news collection (about a minute).
4. On **Profile**, click **Send verification code**, enter the code from your inbox, then
   **Send Notification Now**. This confirms email sending works from the server.

Logs, if something fails:

```bash
docker compose --env-file deploy/production.env -f docker-compose.prod.yml logs -f backend
docker compose --env-file deploy/production.env -f docker-compose.prod.yml logs caddy
```

Common problems:

- **No certificate / site unreachable:** ports 80 and 443 not open (step 1 security list, step 3 firewall), or the domain does not point at the server yet.
- **Email fails with "Network is unreachable" or a timeout:** the provider blocks port 587. Use another provider or ask them to unblock it.
- **Backend keeps restarting with a SECRET_KEY error:** `SECRET_KEY` is missing or shorter than 32 characters.

## Keeping it running

**Update to the latest code:**

```bash
cd ~/CandorNews && git pull
docker compose --env-file deploy/production.env -f docker-compose.prod.yml up -d --build
```

**Back up the database** (keep copies off the server too):

```bash
docker compose --env-file deploy/production.env -f docker-compose.prod.yml exec -T mongodb \
  mongodump --archive --gzip --db news_intelligence > backup-$(date +%F).archive.gz
```

**Copy your local data to the server (optional).** On your computer:

```bash
docker exec newscollectbot-mongodb-1 mongodump --archive --gzip --db news_intelligence > local.archive.gz
scp local.archive.gz ubuntu@<server-ip>:~/CandorNews/
```

On the server:

```bash
docker compose --env-file deploy/production.env -f docker-compose.prod.yml exec -T mongodb \
  mongorestore --archive --gzip --drop < local.archive.gz
```

Account emails must be verified again only if they were never verified.

## Rules for this setup

- Run **one** backend container only; refresh jobs and the email scheduler live in that process.
- Never commit `deploy/production.env`.
- MongoDB has no published port; do not add one.

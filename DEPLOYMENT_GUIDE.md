# Deploying CandorNews on Azure for Students

This puts the whole system (website, API, MongoDB, news collector and email
scheduler) on one small Linux server using `docker-compose.prod.yml`. Caddy
serves the site over HTTPS and is the only part reachable from the internet.

```
Internet ──443──> Caddy ──/api, /health──> backend (FastAPI, collector, email scheduler)
                     └────────other───────> frontend (React, Nginx)
                                            backend ──> MongoDB (private)
```

**You need:** your university email (for Azure for Students), and your Gmail
App Password. Sign-ups and passwords are entered by you. Expect about one hour.

## 1. Activate Azure for Students

1. Go to <https://azure.microsoft.com/free/students/> and sign up with your **university email**.
   No credit card is required. You get **US$100 credit for 12 months**, renewable each year while you are a student.
2. In the Azure portal, open **Cost Management → Budgets** and create a budget of **US$10** with an
   email alert at 50%. The setup below should cost only a few dollars a month from the credit
   (mainly the public IP address), and the alert tells you if anything costs more.

When the credit runs out the subscription is paused; your card is never charged.

## 2. Create the server

1. In the portal search for **Free services** and create the **Linux Virtual Machine** from there
   (this keeps you on the free-eligible options).
2. Settings:
   - **Region:** the closest region your subscription allows. Try **Southeast Asia** first. If you get
     "RequestDisallowedByAzure" or the region is missing, pick another listed region (for example
     East Asia, Japan East or Central India). Student subscriptions only allow certain regions.
   - **Image:** Ubuntu Server **24.04 LTS** (x64).
   - **Size:** **B2ats v2** (2 vCPU, 1 GiB) if offered as free, otherwise **B1s** (1 vCPU, 1 GiB).
   - **Authentication:** SSH public key; username `azureuser`. Download the private key when asked and keep it safe.
   - **Inbound ports:** allow **SSH (22), HTTP (80), HTTPS (443)**.
   - **Disks:** keep the default OS disk only. Do not add extra or Premium disks.
   - **Management tab:** make sure **Auto-shutdown is OFF**. Otherwise the server stops every night
     and the news collector and email digests stop with it.
3. Create the VM and wait for it to finish.
4. Open the VM → **Networking**. Optional hardening: change the SSH rule's source from *Any* to *My IP address*.

## 3. Get the web address (free)

Open the VM → **Overview → DNS name → Not configured**, set a **DNS name label** such as `candornews`,
and save. Your site address becomes:

```
candornews.<region>.cloudapp.azure.com     (for example candornews.southeastasia.cloudapp.azure.com)
```

If the page asks, set the public IP **Assignment** to **Static** so the address never changes.
This is your `DOMAIN`. Caddy will get the HTTPS certificate for it automatically.

## 4. Prepare the server

Connect from your computer (PowerShell or Terminal):

```bash
ssh -i path/to/your-key.pem azureuser@<DOMAIN>
```

Then on the server:

```bash
sudo apt-get update && sudo apt-get -y upgrade
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# 1 GB servers need swap, especially for building the website
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
exit
```

Connect again (so the `docker` group applies).

## 5. Get the code and add the settings

```bash
git clone https://github.com/CJC030820/CandorNews.git
cd CandorNews
cp deploy/production.env.example deploy/production.env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # copy this for SECRET_KEY
nano deploy/production.env
```

Fill in:

| Setting | Value |
|---|---|
| `DOMAIN` | your address from step 3, without `https://` |
| `SECRET_KEY` | the random value printed above |
| `CORS_ORIGINS` | `https://` + your address |
| `SMTP_USERNAME`, `SMTP_FROM_EMAIL` | your Gmail address |
| `SMTP_PASSWORD` | your Gmail **App Password** |

Save (Ctrl+O, Enter, Ctrl+X), then protect the file:

```bash
chmod 600 deploy/production.env
```

## 6. Start it

```bash
docker compose --env-file deploy/production.env -f docker-compose.prod.yml up -d --build
docker compose --env-file deploy/production.env -f docker-compose.prod.yml ps
```

The first build takes **10–20 minutes** on a 1 GB server. All four services should show `running`.

## 7. Check it works

1. Open `https://<DOMAIN>`. The padlock should show and the login page should load.
2. `https://<DOMAIN>/health` should show `"status":"healthy"`.
3. Register an account, choose topics, and wait about a minute for the first news collection.
4. On **Profile**, click **Send verification code**, enter the code from your inbox, then
   **Send Notification Now**. This confirms email sending works from Azure (port 587 is allowed).

Logs, if something fails:

```bash
docker compose --env-file deploy/production.env -f docker-compose.prod.yml logs -f backend
docker compose --env-file deploy/production.env -f docker-compose.prod.yml logs caddy
```

Common problems:

- **Site unreachable or no certificate:** ports 80/443 not allowed in the VM's Networking rules, or the DNS name label is not set.
- **Build stops or the server freezes:** swap is missing (step 4). Check with `free -h`.
- **Backend keeps restarting with a SECRET_KEY error:** `SECRET_KEY` is missing or shorter than 32 characters.
- **Email: "SMTP authentication failed":** use a Gmail App Password, not your normal password.
- **Site stopped overnight:** auto-shutdown is on (VM → Auto-shutdown → Off), then start the VM again.

## Keeping it running

**Update to the latest code:**

```bash
cd ~/CandorNews && git pull
docker compose --env-file deploy/production.env -f docker-compose.prod.yml up -d --build
```

**Back up the database** and copy the file off the server:

```bash
docker compose --env-file deploy/production.env -f docker-compose.prod.yml exec -T mongodb \
  mongodump --archive --gzip --db news_intelligence > backup-$(date +%F).archive.gz
```

From your computer: `scp -i path/to/your-key.pem azureuser@<DOMAIN>:~/CandorNews/backup-*.archive.gz .`

**Copy your local news data to the server (optional).** On your computer:

```bash
docker exec newscollectbot-mongodb-1 mongodump --archive --gzip --db news_intelligence > local.archive.gz
scp -i path/to/your-key.pem local.archive.gz azureuser@<DOMAIN>:~/CandorNews/
```

On the server:

```bash
docker compose --env-file deploy/production.env -f docker-compose.prod.yml exec -T mongodb \
  mongorestore --archive --gzip --drop < local.archive.gz
```

**Check spending** now and then under Cost Management. Stop the VM (Overview → Stop) when you do not
need it; a stopped VM does not use compute hours, but the static public IP is still charged.

## Rules for this setup

- Run **one** backend container only; refresh jobs and the email scheduler live in that process.
- Never commit `deploy/production.env`.
- MongoDB has no published port; do not add one.

## Other servers

The same steps work on any Ubuntu server with Docker. Differences:

- **Oracle Cloud Always Free:** open TCP 80/443 in the VCN Security List **and** in the server firewall
  (`sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT`, the same for 443,
  then `sudo netfilter-persistent save`). Use a domain from DuckDNS or `<server-ip>.sslip.io`.
- **Other providers:** make sure outgoing port 587 (email) is allowed.

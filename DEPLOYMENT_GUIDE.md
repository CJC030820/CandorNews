# Production Deployment Guide - News Intelligence System v2.0

## 📋 Pre-Deployment Checklist

### Security
- [ ] Generate a new `SECRET_KEY`: `openssl rand -hex 32`
- [ ] Update `backend/.env` with production values
- [ ] Use a real secret manager (AWS Secrets Manager, HashiCorp Vault, etc.)
- [ ] Change `ALLOWED_ORIGINS` to specific domains (remove `localhost`)
- [ ] Enable HTTPS/TLS for all services
- [ ] Set up authentication for MongoDB (not just network access)
- [ ] Remove all `.env` files from git (already in `.gitignore`)

### Configuration
- [ ] Configure real MongoDB Atlas or managed MongoDB service
- [ ] Set up real mail service (Gmail App Password, SendGrid, etc.)
- [ ] Get and configure NewsAPI and GNews API keys
- [ ] Set up LaunchDarkly for feature flags (optional)
- [ ] Configure RSS feed sources for your region

### Infrastructure
- [ ] Choose deployment platform (AWS ECS, Google Cloud Run, DigitalOcean, etc.)
- [ ] Set up container registry (Docker Hub, AWS ECR, etc.)
- [ ] Configure CI/CD pipeline (GitHub Actions, GitLab CI, etc.)
- [ ] Set up monitoring and logging (Datadog, New Relic, ELK Stack, etc.)
- [ ] Configure auto-scaling policies
- [ ] Set up backup strategy for MongoDB

---

## 🚀 Deployment Options

### Option 1: Docker Compose on a Single Server (Simple)

**Best for:** Small deployments, prototypes, single-host setups

```bash
# 1. SSH into your server
ssh user@your-server.com

# 2. Clone the repository
git clone https://github.com/yourorg/newscollectbot.git
cd newscollectbot

# 3. Create production .env
cp backend/.env.example backend/.env
# Edit backend/.env with real secrets and production URLs

# 4. Pull latest and build
git pull
docker compose -f docker-compose.yml build

# 5. Start with production settings
docker compose -f docker-compose.yml up -d

# 6. Verify
docker compose ps
docker compose logs backend
```

**Reverse Proxy Setup (Nginx):**

```nginx
upstream backend {
    server backend:8080;
}

upstream frontend {
    server frontend:80;
}

server {
    listen 443 ssl http2;
    server_name news.example.com;

    ssl_certificate /etc/letsencrypt/live/news.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/news.example.com/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    # API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 30s;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name news.example.com;
    return 301 https://$server_name$request_uri;
}
```

---

### Option 2: AWS ECS with Fargate (Scalable)

**Best for:** Production workloads, high availability, auto-scaling

#### Step 1: Set up ECR repositories

```bash
aws ecr create-repository --repository-name news-backend --region us-east-1
aws ecr create-repository --repository-name news-frontend --region us-east-1
aws ecr create-repository --repository-name news-mongodb --region us-east-1
```

#### Step 2: Build and push images

```bash
# Backend
docker build -t news-backend:latest ./backend
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin [ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com
docker tag news-backend:latest [ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com/news-backend:latest
docker push [ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com/news-backend:latest

# Frontend
docker build -t news-frontend:latest ./frontend
docker tag news-frontend:latest [ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com/news-frontend:latest
docker push [ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com/news-frontend:latest
```

#### Step 3: Create ECS cluster and services

```bash
# Create cluster
aws ecs create-cluster --cluster-name news-cluster --region us-east-1

# Create task definitions (see below)
aws ecs register-task-definition --cli-input-json file://backend-task-def.json
aws ecs register-task-definition --cli-input-json file://frontend-task-def.json

# Create services
aws ecs create-service \
    --cluster news-cluster \
    --service-name news-backend \
    --task-definition news-backend:1 \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"

aws ecs create-service \
    --cluster news-cluster \
    --service-name news-frontend \
    --task-definition news-frontend:1 \
    --desired-count 2 \
    --launch-type FARGATE \
    --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=frontend,containerPort=80
```

#### Step 4: Use AWS Secrets Manager

```bash
# Store secrets
aws secretsmanager create-secret \
    --name news/backend/env \
    --secret-string file://backend/.env.production

# Reference in task definition:
{
  "environment": [
    {
      "name": "NEWSAPI_KEY",
      "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:news/backend/env:NEWSAPI_KEY::"
    }
  ]
}
```

---

### Option 3: Google Cloud Run (Serverless)

**Best for:** Low-cost, auto-scaling, minimal ops

```bash
# 1. Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/news-backend ./backend
gcloud builds submit --tag gcr.io/PROJECT_ID/news-frontend ./frontend

# 2. Deploy backend
gcloud run deploy news-backend \
    --image gcr.io/PROJECT_ID/news-backend \
    --platform managed \
    --region us-central1 \
    --memory 1Gi \
    --cpu 1 \
    --set-env-vars MONGODB_URL=mongodb+srv://user:pass@cluster.mongodb.net/news \
    --allow-unauthenticated

# 3. Deploy frontend
gcloud run deploy news-frontend \
    --image gcr.io/PROJECT_ID/news-frontend \
    --platform managed \
    --region us-central1 \
    --memory 512Mi \
    --set-env-vars REACT_APP_API_URL=https://news-backend-xxx.run.app \
    --allow-unauthenticated

# 4. Set up Cloud Load Balancer for both services
```

---

## 🔐 Environment Variables for Production

```bash
# Core
SECRET_KEY=<64-char hex from openssl rand -hex 32>
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/news_intelligence?retryWrites=true&w=majority
DATABASE_NAME=news_intelligence
ALLOWED_ORIGINS=https://news.example.com,https://www.news.example.com

# News APIs (sign up for free)
NEWSAPI_KEY=<your-key-from-newsapi.org>
GNEWS_API_KEY=<your-key-from-gnews.io>

# Email (use production SMTP service)
SMTP_HOST=smtp.sendgrid.net  # or smtp.gmail.com with App Password
SMTP_PORT=587
SMTP_USERNAME=apikey  # for SendGrid
SMTP_PASSWORD=<your-sendgrid-api-key>
SMTP_FROM_EMAIL=noreply@news.example.com
SMTP_FROM_NAME=News Intelligence

# JWT (production should be shorter)
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours instead of 30 days

# Feature flags (optional)
LD_SDK_KEY=<your-launchdarkly-sdk-key>

# Worker settings
WORKER_INTERVAL_MINUTES=30
TRUST_WEIGHT_SOURCE_REPUTATION=0.40
TRUST_WEIGHT_CROSS_SOURCE=0.35
TRUST_WEIGHT_SEMANTIC_SIMILARITY=0.00
TRUST_WEIGHT_HEADLINE_CONSISTENCY=0.12
TRUST_WEIGHT_METADATA_COMPLETENESS=0.13
```

---

## 📊 Monitoring & Logging Setup

### Application Logging

```python
# In backend/app/main.py
import logging
from pythonjsonlogger import jsonlogger

# JSON logging for better parsing
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logging.root.addHandler(logHandler)
logging.root.setLevel(logging.INFO)
```

### Health Checks

```bash
# Monitor backend health
curl https://news.example.com/api/health

# Monitor frontend
curl https://news.example.com/ | grep -q "react" && echo "✓ Frontend OK" || echo "✗ Frontend Failed"
```

### Set up alerts

- Backend HTTP errors (5xx responses)
- MongoDB connection failures
- High response latency (>3s for feed endpoint)
- Worker job failures
- Low disk space on MongoDB volume

---

## 🔄 CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run tests
        run: |
          docker compose -f docker-compose.test.yml up --abort-on-container-exit
      
      - name: Push to registry
        run: |
          echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
          docker build -t myrepo/news-backend:${{ github.sha }} ./backend
          docker build -t myrepo/news-frontend:${{ github.sha }} ./frontend
          docker push myrepo/news-backend:${{ github.sha }}
          docker push myrepo/news-frontend:${{ github.sha }}
      
      - name: Deploy to production
        run: |
          # Update your deployment with new image tags
          # This depends on your orchestration choice (Docker Compose, ECS, K8s, etc.)
```

---

## 📦 Backup & Recovery Strategy

### MongoDB Backups

```bash
# Automated daily backup to S3
mongobackup --uri $MONGODB_URL --out ./backup-$(date +%Y%m%d)
aws s3 sync ./backup-* s3://news-backups/mongo/

# Restore from backup
mongorestore --uri $MONGODB_URL --drop ./backup-20240810
```

### Database Snapshots

- Use MongoDB Atlas automated backups (if using Atlas)
- Or enable EBS snapshots for self-hosted MongoDB
- Test restore process monthly

---

## 🚨 Troubleshooting Deployment Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Backend connection refused | MongoDB not ready | Add `depends_on` with health checks |
| Frontend blank page | API URL misconfigured | Check `REACT_APP_API_URL` env var |
| Auth token invalid | SECRET_KEY mismatch | Ensure same SECRET_KEY across all instances |
| High memory usage | ML models not unloading | Implement model cleanup in worker |
| Slow feed response | Large database scans | Add indexes on `topic`, `processing_status` |
| CORS errors | Origin not in whitelist | Update `ALLOWED_ORIGINS` |

---

## ✅ Post-Deployment Verification

```bash
# 1. Frontend accessibility
curl -I https://news.example.com

# 2. API endpoints
curl -H "Authorization: Bearer $TOKEN" https://news.example.com/api/health

# 3. Database connectivity
mongosh "mongodb+srv://user:pass@cluster.mongodb.net" --eval "db.adminCommand('ping')"

# 4. Run integration tests
python test_system_integration.py --api-url https://news.example.com

# 5. Monitor logs
docker compose logs -f backend
kubectl logs -f deployment/news-backend  # if using k8s
aws logs tail /ecs/news-backend --follow  # if using ECS
```

---

## 📚 Additional Resources

- [Docker Compose Production Setup](https://docs.docker.com/compose/compose-file/compose-file-v3/#services)
- [AWS ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html)
- [MongoDB Atlas Security](https://docs.atlas.mongodb.com/security/)
- [FastAPI Production Deployment](https://fastapi.tiangolo.com/deployment/)
- [React Production Build Optimization](https://create-react-app.dev/docs/production-build/)

---

**Need help?** See `SYSTEM_UPDATE_v2.0.md` or check backend logs: `docker compose logs backend`

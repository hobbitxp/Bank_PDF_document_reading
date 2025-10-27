# AWS Lightsail Deployment Guide

## Overview
Deploy Bank Statement Analyzer on AWS Lightsail for **$5/month**.

### Specifications
- **Instance**: Lightsail Nano ($5/month)
- **Resources**: 1GB RAM, 1 vCPU, 40GB SSD
- **Region**: ap-southeast-1 (Singapore)
- **Storage**: S3 (same bucket as dev, `prod/` prefix)
- **Database**: PostgreSQL (Docker container)

## Cost Breakdown

| Service | Cost | Notes |
|---------|------|-------|
| Lightsail Nano | $5/month | Fixed price, includes 2TB bandwidth |
| S3 Storage | ~$0.12/month | 5GB at $0.023/GB (Free Tier: 5GB free for 12 months) |
| S3 Requests | ~$0.01/month | GET/PUT requests (Free Tier: 20K GET, 2K PUT free) |
| **Total** | **~$5.13/month** | Almost free with AWS Free Tier |

## Prerequisites

1. **AWS CLI configured**:
   ```bash
   aws configure
   ```

2. **Git repository access**:
   ```bash
   git clone https://github.com/hobbitxp/Bank_PDF_document_reading.git
   cd Bank_PDF_document_reading
   ```

3. **Environment file ready**:
   ```bash
   cp .env.dev .env.production
   # Edit .env.production with production values
   ```

## Deployment Steps

### Step 1: Create Lightsail Instance

```bash
./scripts/create-lightsail-instance.sh
```

**What it does:**
- Creates SSH key pair (`~/.ssh/bank-app-key.pem`)
- Launches Lightsail instance ($5/month)
- Allocates static IP address
- Opens firewall ports (22, 80, 8001)

**Expected output:**
```
🎉 Lightsail Instance Created!
========================================
Instance Details:
  Name: bank-statement-analyzer
  Plan: nano_3_0 ($5/month)
  Static IP: 13.214.123.45
  SSH Key: ~/.ssh/bank-app-key.pem
```

### Step 2: Deploy Application

```bash
./scripts/deploy-to-lightsail.sh <STATIC_IP>
```

Example:
```bash
./scripts/deploy-to-lightsail.sh 13.214.123.45
```

**What it does:**
- Installs Docker & Docker Compose
- Clones repository
- Copies `.env.production`
- Starts Docker containers (FastAPI + PostgreSQL)
- Runs health check

**Expected output:**
```
🎉 Deployment Complete!
========================================
API Endpoints:
  Swagger Docs: http://13.214.123.45:8001/docs
  Health Check: http://13.214.123.45:8001/health
  Analyze API:  http://13.214.123.45:8001/api/v1/analyze-upload
```

## S3 Folder Structure

With `ENVIRONMENT=prod`, files are stored with prefix:

```
s3://analyze-bank-statement-dev/
├── dev/                    # Local development
│   ├── test_user/
│   │   └── 2025-10-27_statement.pdf
│   └── ...
└── prod/                   # Production (Lightsail)
    ├── user_001/
    │   └── 2025-10-27_statement.pdf
    └── ...
```

## Accessing the Instance

### SSH Access
```bash
ssh -i ~/.ssh/bank-app-key.pem ubuntu@<STATIC_IP>
```

### View Logs
```bash
ssh -i ~/.ssh/bank-app-key.pem ubuntu@<STATIC_IP> \
  'cd Bank_PDF_document_reading && docker-compose logs -f'
```

### Restart Services
```bash
ssh -i ~/.ssh/bank-app-key.pem ubuntu@<STATIC_IP> \
  'cd Bank_PDF_document_reading && docker-compose restart'
```

### Update Code
```bash
ssh -i ~/.ssh/bank-app-key.pem ubuntu@<STATIC_IP> << 'ENDSSH'
  cd Bank_PDF_document_reading
  git pull
  docker-compose up -d --build
ENDSSH
```

## Testing the Deployment

### 1. Health Check
```bash
curl http://<STATIC_IP>:8001/health
```

Expected:
```json
{"status": "healthy"}
```

### 2. API Documentation
Open in browser:
```
http://<STATIC_IP>:8001/docs
```

### 3. Upload Test PDF
```bash
curl -X POST http://<STATIC_IP>:8001/api/v1/analyze-upload \
  -F "pdf_file=@test.pdf" \
  -F "user_id=test_prod" \
  -F "income_type=salaried"
```

Check S3:
```bash
aws s3 ls s3://analyze-bank-statement-dev/prod/test_prod/
```

## Monitoring

### Check Container Status
```bash
ssh -i ~/.ssh/bank-app-key.pem ubuntu@<STATIC_IP> \
  'docker-compose ps'
```

### View PostgreSQL Data
```bash
ssh -i ~/.ssh/bank-app-key.pem ubuntu@<STATIC_IP> \
  'docker exec -it bank_statement_db psql -U bank_app_prod -d bank_statement_prod -c "SELECT COUNT(*) FROM analyses;"'
```

### Check S3 Usage
```bash
aws s3 ls s3://analyze-bank-statement-dev/prod/ --recursive --human-readable --summarize
```

## Cleanup (Delete Instance)

⚠️ **Warning**: This will delete all data on the instance!

```bash
# Delete instance
aws lightsail delete-instance --instance-name bank-statement-analyzer

# Release static IP
aws lightsail release-static-ip --static-ip-name bank-statement-analyzer-static-ip

# Delete key pair (optional)
aws lightsail delete-key-pair --key-pair-name bank-app-key
rm ~/.ssh/bank-app-key.pem
```

## Cost Optimization Tips

1. **Use Free Tier benefits** (12 months):
   - 750 hours/month EC2 equivalent (fully covered by Lightsail)
   - 5GB S3 storage free
   - 20,000 GET requests free

2. **Enable S3 Lifecycle** to delete old PDFs:
   ```bash
   aws s3api put-bucket-lifecycle-configuration \
     --bucket analyze-bank-statement-dev \
     --lifecycle-configuration file://s3-lifecycle.json
   ```

3. **Monitor usage**:
   ```bash
   # Check Lightsail bandwidth
   aws lightsail get-instance-metric-data \
     --instance-name bank-statement-analyzer \
     --metric-name NetworkIn \
     --start-time 2025-10-01T00:00:00Z \
     --end-time 2025-10-31T23:59:59Z \
     --period 86400 \
     --statistics Sum
   ```

## Troubleshooting

### API not responding
```bash
ssh -i ~/.ssh/bank-app-key.pem ubuntu@<STATIC_IP> \
  'cd Bank_PDF_document_reading && docker-compose logs bank_statement_api'
```

### Database connection error
```bash
ssh -i ~/.ssh/bank-app-key.pem ubuntu@<STATIC_IP> \
  'docker exec -it bank_statement_db psql -U bank_app_prod -d bank_statement_prod -c "\l"'
```

### S3 upload fails
Check AWS credentials in `.env`:
```bash
ssh -i ~/.ssh/bank-app-key.pem ubuntu@<STATIC_IP> \
  'cat Bank_PDF_document_reading/.env | grep AWS'
```

## Security Best Practices

1. **Change default database password**:
   ```bash
   # Already done automatically in deploy script
   # Uses: openssl rand -base64 32
   ```

2. **Restrict SSH access** (optional):
   ```bash
   aws lightsail update-instance-access \
     --instance-name bank-statement-analyzer \
     --access-rules "allowPublicIpv4=false,allowedIps=YOUR_IP/32"
   ```

3. **Enable HTTPS** (optional, requires domain):
   - Use Nginx reverse proxy
   - Get free SSL from Let's Encrypt
   - See: `scripts/setup-https.sh` (TODO)

## Next Steps

- [ ] Set up automated backups (Lightsail snapshots)
- [ ] Configure CloudWatch alarms for monitoring
- [ ] Add CI/CD pipeline (GitHub Actions → Lightsail)
- [ ] Implement rate limiting (nginx)
- [ ] Add SSL certificate (if using domain)

## Support

For issues or questions:
- GitHub Issues: https://github.com/hobbitxp/Bank_PDF_document_reading/issues
- Email: [your-email]

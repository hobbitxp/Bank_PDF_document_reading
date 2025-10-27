#!/bin/bash
# Deploy application to Lightsail instance

set -e

if [ -z "$1" ]; then
    echo "Usage: ./deploy-to-lightsail.sh <INSTANCE_IP>"
    echo "Example: ./deploy-to-lightsail.sh 13.214.123.45"
    exit 1
fi

INSTANCE_IP=$1
SSH_KEY=~/.ssh/bank-app-key
SSH_USER=ubuntu

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🚀 Deploying to Lightsail: $INSTANCE_IP"
echo "========================================"

# Step 1: Install Docker and Docker Compose
echo -e "${YELLOW}Step 1: Installing Docker...${NC}"
ssh -i $SSH_KEY $SSH_USER@$INSTANCE_IP << 'ENDSSH'
    # Update system
    sudo apt-get update
    sudo apt-get upgrade -y
    
    # Install Docker
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker ubuntu
    
    # Install Docker Compose
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    # Verify installation
    docker --version
    docker-compose --version
    
    echo "✅ Docker installed"
ENDSSH

# Step 2: Clone repository
echo -e "${YELLOW}Step 2: Cloning repository...${NC}"
ssh -i $SSH_KEY $SSH_USER@$INSTANCE_IP << 'ENDSSH'
    if [ -d "Bank_PDF_document_reading" ]; then
        cd Bank_PDF_document_reading
        git pull
    else
        git clone https://github.com/hobbitxp/Bank_PDF_document_reading.git
        cd Bank_PDF_document_reading
    fi
    echo "✅ Repository ready"
ENDSSH

# Step 3: Copy environment file
echo -e "${YELLOW}Step 3: Setting up environment...${NC}"
scp -i $SSH_KEY .env.production $SSH_USER@$INSTANCE_IP:~/Bank_PDF_document_reading/.env

# Step 4: Update .env with AWS credentials from local
echo -e "${YELLOW}Step 4: Updating AWS credentials...${NC}"
AWS_KEY=$(grep AWS_ACCESS_KEY_ID .env.dev | cut -d'=' -f2)
AWS_SECRET=$(grep AWS_SECRET_ACCESS_KEY .env.dev | cut -d'=' -f2)

ssh -i $SSH_KEY $SSH_USER@$INSTANCE_IP << ENDSSH
    cd Bank_PDF_document_reading
    sed -i "s/AWS_ACCESS_KEY_ID=.*/AWS_ACCESS_KEY_ID=$AWS_KEY/" .env
    sed -i "s/AWS_SECRET_ACCESS_KEY=.*/AWS_SECRET_ACCESS_KEY=$AWS_SECRET/" .env
    sed -i "s/DB_PASSWORD=CHANGE_ME_STRONG_PASSWORD/DB_PASSWORD=$(openssl rand -base64 32)/" .env
    echo "✅ Environment configured"
ENDSSH

# Step 5: Start Docker containers
echo -e "${YELLOW}Step 5: Starting Docker containers...${NC}"
ssh -i $SSH_KEY $SSH_USER@$INSTANCE_IP << 'ENDSSH'
    cd Bank_PDF_document_reading
    docker-compose down || true
    docker-compose up -d --build
    
    # Wait for services
    sleep 10
    docker-compose ps
    
    echo "✅ Containers started"
ENDSSH

# Step 6: Check API health
echo -e "${YELLOW}Step 6: Checking API health...${NC}"
sleep 5
if curl -sf http://$INSTANCE_IP:8001/health > /dev/null; then
    echo -e "${GREEN}✅ API is healthy!${NC}"
else
    echo -e "${RED}❌ API health check failed${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "API Endpoints:"
echo "  Swagger Docs: http://$INSTANCE_IP:8001/docs"
echo "  Health Check: http://$INSTANCE_IP:8001/health"
echo "  Analyze API:  http://$INSTANCE_IP:8001/api/v1/analyze-upload"
echo ""
echo "Useful Commands:"
echo "  SSH: ssh -i $SSH_KEY $SSH_USER@$INSTANCE_IP"
echo "  Logs: ssh -i $SSH_KEY $SSH_USER@$INSTANCE_IP 'cd Bank_PDF_document_reading && docker-compose logs -f'"
echo "  Restart: ssh -i $SSH_KEY $SSH_USER@$INSTANCE_IP 'cd Bank_PDF_document_reading && docker-compose restart'"
echo ""

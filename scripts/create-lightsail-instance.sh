#!/bin/bash
# AWS Lightsail Instance Setup Script
# This script creates a Lightsail $5/month instance and deploys the bank statement analyzer

set -e

echo "🚀 AWS Lightsail Deployment Script"
echo "===================================="

# Configuration
INSTANCE_NAME="bank-statement-analyzer"
BLUEPRINT_ID="ubuntu_24_04"
BUNDLE_ID="nano_3_0"  # $5/month: 1GB RAM, 1 vCPU, 40GB SSD
AVAILABILITY_ZONE="ap-southeast-1a"  # Singapore
KEY_PAIR_NAME="bank-app-key"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Create SSH key pair if not exists
echo -e "${YELLOW}Step 1: Checking SSH key pair...${NC}"
if ! aws lightsail get-key-pair --key-pair-name "$KEY_PAIR_NAME" &>/dev/null; then
    echo "Key pair not found in AWS. Checking local key..."
    if [ ! -f ~/.ssh/bank-app-key ]; then
        echo "Creating new SSH key pair locally..."
        ssh-keygen -t rsa -b 4096 -f ~/.ssh/bank-app-key -N "" -C "bank-app-lightsail"
        chmod 400 ~/.ssh/bank-app-key
    fi
    echo "Importing public key to AWS Lightsail..."
    aws lightsail import-key-pair \
        --key-pair-name "$KEY_PAIR_NAME" \
        --public-key-base64 file://~/.ssh/bank-app-key.pub
    echo -e "${GREEN}✅ Key pair imported: ~/.ssh/bank-app-key${NC}"
else
    echo -e "${GREEN}✅ Key pair already exists in AWS${NC}"
    if [ ! -f ~/.ssh/bank-app-key ]; then
        echo -e "${RED}⚠️  Local key file missing! You may need to use Lightsail console for SSH${NC}"
    fi
fi

# Step 2: Check if instance already exists
echo -e "${YELLOW}Step 2: Checking if instance exists...${NC}"
if aws lightsail get-instance --instance-name "$INSTANCE_NAME" &>/dev/null; then
    echo -e "${RED}❌ Instance '$INSTANCE_NAME' already exists!${NC}"
    echo "Delete it first with: aws lightsail delete-instance --instance-name $INSTANCE_NAME"
    exit 1
fi

# Step 3: Create Lightsail instance
echo -e "${YELLOW}Step 3: Creating Lightsail instance ($BUNDLE_ID = \$5/month)...${NC}"
aws lightsail create-instances \
    --instance-names "$INSTANCE_NAME" \
    --availability-zone "$AVAILABILITY_ZONE" \
    --blueprint-id "$BLUEPRINT_ID" \
    --bundle-id "$BUNDLE_ID" \
    --key-pair-name "$KEY_PAIR_NAME" \
    --tags "key=Project,value=BankStatementAnalyzer" "key=Environment,value=production"

echo -e "${GREEN}✅ Instance creation initiated${NC}"

# Step 4: Wait for instance to be running
echo -e "${YELLOW}Step 4: Waiting for instance to be ready (this takes ~2 minutes)...${NC}"
for i in {1..60}; do
    STATE=$(aws lightsail get-instance --instance-name "$INSTANCE_NAME" --query 'instance.state.name' --output text)
    if [ "$STATE" == "running" ]; then
        echo -e "${GREEN}✅ Instance is running!${NC}"
        break
    fi
    echo -n "."
    sleep 5
done

# Step 5: Get public IP
echo -e "${YELLOW}Step 5: Getting public IP...${NC}"
PUBLIC_IP=$(aws lightsail get-instance --instance-name "$INSTANCE_NAME" --query 'instance.publicIpAddress' --output text)
echo -e "${GREEN}✅ Public IP: $PUBLIC_IP${NC}"

# Step 6: Open firewall ports
echo -e "${YELLOW}Step 6: Opening firewall ports (8001 for API)...${NC}"
aws lightsail open-instance-public-ports \
    --instance-name "$INSTANCE_NAME" \
    --port-info fromPort=8001,toPort=8001,protocol=TCP

aws lightsail open-instance-public-ports \
    --instance-name "$INSTANCE_NAME" \
    --port-info fromPort=80,toPort=80,protocol=TCP

echo -e "${GREEN}✅ Ports opened: 22 (SSH), 80 (HTTP), 8001 (API)${NC}"

# Step 7: Allocate static IP
echo -e "${YELLOW}Step 7: Allocating static IP...${NC}"
aws lightsail allocate-static-ip \
    --static-ip-name "${INSTANCE_NAME}-static-ip"

aws lightsail attach-static-ip \
    --static-ip-name "${INSTANCE_NAME}-static-ip" \
    --instance-name "$INSTANCE_NAME"

STATIC_IP=$(aws lightsail get-static-ip --static-ip-name "${INSTANCE_NAME}-static-ip" --query 'staticIp.ipAddress' --output text)
echo -e "${GREEN}✅ Static IP allocated: $STATIC_IP${NC}"

# Step 8: Wait for SSH to be ready
echo -e "${YELLOW}Step 8: Waiting for SSH to be ready...${NC}"
sleep 30
for i in {1..20}; do
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i ~/.ssh/bank-app-key ubuntu@$STATIC_IP "echo 'SSH Ready'" &>/dev/null; then
        echo -e "${GREEN}✅ SSH is ready!${NC}"
        break
    fi
    echo -n "."
    sleep 5
done

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 Lightsail Instance Created!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Instance Details:"
echo "  Name: $INSTANCE_NAME"
echo "  Plan: $BUNDLE_ID (\$5/month)"
echo "  Static IP: $STATIC_IP"
echo "  SSH Key: ~/.ssh/bank-app-key"
echo ""
echo "Next Steps:"
echo "  1. SSH into instance:"
echo "     ssh -i ~/.ssh/bank-app-key ubuntu@$STATIC_IP"
echo ""
echo "  2. Run deployment script:"
echo "     ./scripts/deploy-to-lightsail.sh $STATIC_IP"
echo ""
echo "  3. Access API:"
echo "     http://$STATIC_IP:8001/docs"
echo ""

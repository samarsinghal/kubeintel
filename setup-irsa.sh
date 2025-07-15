#!/bin/bash

# KubeIntel IRSA (IAM Roles for Service Accounts) Setup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔐 Setting up IRSA for KubeIntel${NC}"

# Check required parameters
CLUSTER_NAME=${CLUSTER_NAME:-$(kubectl config current-context | cut -d'/' -f2 2>/dev/null || echo "")}
ROLE_NAME=${ROLE_NAME:-KubeIntelAgentRole}
NAMESPACE=${NAMESPACE:-kubeintel}
SERVICE_ACCOUNT=${SERVICE_ACCOUNT:-kubeintel-agent}

if [[ -z "$CLUSTER_NAME" ]]; then
    echo -e "${RED}❌ CLUSTER_NAME not found. Please set it or ensure kubectl context is set${NC}"
    echo -e "${YELLOW}💡 Example: export CLUSTER_NAME=my-eks-cluster${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 IRSA Configuration:${NC}"
echo "  Cluster Name: $CLUSTER_NAME"
echo "  Role Name: $ROLE_NAME"
echo "  Namespace: $NAMESPACE"
echo "  Service Account: $SERVICE_ACCOUNT"

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "  AWS Account: $ACCOUNT_ID"

# Get OIDC issuer
echo -e "${YELLOW}🔍 Getting OIDC issuer...${NC}"
OIDC_ISSUER=$(aws eks describe-cluster --name $CLUSTER_NAME --query 'cluster.identity.oidc.issuer' --output text)
OIDC_ID=$(echo $OIDC_ISSUER | cut -d'/' -f5)
echo "  OIDC Issuer: $OIDC_ISSUER"
echo "  OIDC ID: $OIDC_ID"

# Create trust policy
echo -e "${YELLOW}📝 Creating trust policy...${NC}"
cat > /tmp/kubeintel-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/${OIDC_ID}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.us-east-1.amazonaws.com/id/${OIDC_ID}:sub": "system:serviceaccount:${NAMESPACE}:${SERVICE_ACCOUNT}",
          "oidc.eks.us-east-1.amazonaws.com/id/${OIDC_ID}:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
EOF

# Create IAM role
echo -e "${YELLOW}🏗️  Creating IAM role...${NC}"
if aws iam get-role --role-name $ROLE_NAME >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Role $ROLE_NAME already exists, updating trust policy...${NC}"
    aws iam update-assume-role-policy \
        --role-name $ROLE_NAME \
        --policy-document file:///tmp/kubeintel-trust-policy.json
else
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file:///tmp/kubeintel-trust-policy.json \
        --description "IAM role for KubeIntel agent to access AWS Bedrock"
    echo -e "${GREEN}✅ Created IAM role: $ROLE_NAME${NC}"
fi

# Create custom Bedrock policy for Claude 3.5 models
echo -e "${YELLOW}📝 Creating Claude 3.5 Bedrock policy...${NC}"
cat > /tmp/kubeintel-bedrock-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:GetFoundationModel",
        "bedrock:ListFoundationModels"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create or update the custom policy
POLICY_NAME="KubeIntelClaude35BedrockPolicy"
POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}"

echo -e "${YELLOW}🔗 Creating/updating Bedrock policy...${NC}"
if aws iam get-policy --policy-arn $POLICY_ARN >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Policy $POLICY_NAME already exists, creating new version...${NC}"
    aws iam create-policy-version \
        --policy-arn $POLICY_ARN \
        --policy-document file:///tmp/kubeintel-bedrock-policy.json \
        --set-as-default
else
    aws iam create-policy \
        --policy-name $POLICY_NAME \
        --policy-document file:///tmp/kubeintel-bedrock-policy.json \
        --description "Custom Bedrock policy for KubeIntel with Claude 3.5 model access"
    echo -e "${GREEN}✅ Created custom Bedrock policy: $POLICY_NAME${NC}"
fi

# Attach custom Bedrock policy
echo -e "${YELLOW}🔗 Attaching Claude 3.5 Bedrock permissions...${NC}"
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn $POLICY_ARN

echo -e "${GREEN}✅ IRSA setup complete!${NC}"
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "  1. Deploy KubeIntel with:"
echo "     export AWS_ROLE_ARN=arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
echo "     ./deploy-helm.sh"
echo ""
echo "  2. Or use Helm directly:"
echo "     helm install kubeintel ./helm \\"
echo "       --namespace $NAMESPACE \\"
echo "       --create-namespace \\"
echo "       --set aws.roleArn=arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

# Clean up
rm -f /tmp/kubeintel-trust-policy.json
rm -f /tmp/kubeintel-bedrock-policy.json

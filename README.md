<div align="center">
  <img src="static/images/kubeintel-logo-horizontal.svg" alt="KubeIntel Logo" width="400"/>
</div>

## Overview

KubeIntel is an AI-powered Kubernetes analysis platform that uses AWS Bedrock model to provide intelligent insights about your clusters. Through its FastAPI backend and AWS Strands framework integration, it offers:

- Real-time cluster analysis with AI-powered insights
- Continuous health monitoring and status checks
- Predictive analytics for potential issues
- Resource utilization and optimization recommendations
- Natural language querying of cluster state

### Key Features

- **AI Analysis**: Uses AWS Bedrock to analyze cluster state and provide insights
- **Event Loop System**: Continuous monitoring with predictive analytics
- **Multiple Analysis Modes**:
  - Real-time analysis via REST API
  - Predictive analytics through event loop
- **Comprehensive Tools**:
  - Pod health analysis
  - Service monitoring
  - Event tracking
  - Resource optimization
  - Performance analysis

## Prerequisites

- AWS Account with Bedrock access
- EKS cluster or Kubernetes cluster with AWS connectivity
- AWS CLI configured with appropriate permissions
- kubectl and Helm 3.x installed
- Docker for building images

## Deployment

### 1. Clone Repository
```bash
git clone https://github.com/samarsinghal/kubeintel.git
cd kubeintel
```

### 2. Build and Push Docker Image
```bash
# Set environment variables
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=<your-aws-region>  # Region where Bedrock is enabled for your account

# Create ECR repository
aws ecr create-repository --repository-name kubeintel --region $AWS_REGION

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push image
docker build -t kubeintel:latest .
docker tag kubeintel:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/kubeintel:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/kubeintel:latest
```

### 3. Set Up IRSA (IAM Roles for Service Accounts)
```bash
# Set cluster name
export CLUSTER_NAME="your-cluster-name"
export NAMESPACE="kubeintel"

# Create IRSA role and service account
./setup-irsa.sh
```

### 4. Deploy with Helm
```bash
helm install kubeintel ./helm \
  --namespace kubeintel \
  --create-namespace \
  --set aws.region=$AWS_REGION \
  --set aws.roleArn="arn:aws:iam::$AWS_ACCOUNT_ID:role/KubeIntelAgentRole" \
  --set image.repository="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/kubeintel" \
  --set image.tag=latest \
  --set service.port=80 \
  --set service.targetPort=8000 \
  --set config.strands.region=$AWS_REGION \
  --set config.strands.model=anthropic.claude-3-haiku-20240307-v1:0
```

### 5. Verify Deployment
```bash
# Check deployment status
kubectl rollout status deployment/kubeintel -n kubeintel

# Get LoadBalancer endpoint
export LB_ENDPOINT=$(kubectl get svc kubeintel -n kubeintel -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Test health endpoint
curl http://$LB_ENDPOINT:8000/health

# Test analysis endpoint
curl -X POST http://$LB_ENDPOINT:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "cluster",
    "analysis_request": "What is the overall cluster health status?"
  }'
```

## API Endpoints

- `/health` - Health check and component status
- `/analyze` - Real-time cluster analysis
- `/stream/events` - SSE stream for real-time updates
- `/ws` - WebSocket endpoint for real-time monitoring
- `/namespaces` - List available namespaces
- `/predictions` - Get predictive analytics insights
- `/predictions/detailed` - Get detailed prediction data
- `/dashboard` - Web UI for monitoring and analysis

## Project Structure
```
kubeintel/
├── src/                     # Source code
│   ├── agent/              # Strands agent implementation
│   ├── api/                # FastAPI endpoints
│   ├── event_loop/         # Monitoring and analytics
│   ├── k8s/                # Kubernetes client
│   ├── models/             # Data models
│   └── streaming/          # Real-time streaming
├── tests/                  # Test files
├── static/                 # Web UI assets
├── helm/                   # Helm chart
├── docs/                   # Documentation
├── Dockerfile             # Container definition
└── setup-irsa.sh         # IRSA setup script
```

## Contributing
Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on submitting pull requests.

## License
This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

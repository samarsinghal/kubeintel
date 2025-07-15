# AWS Strands Kubernetes Monitoring Agent Helm Chart

This Helm chart deploys the AWS Strands Kubernetes Monitoring Agent on a Kubernetes cluster.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- AWS credentials with Bedrock access (optional)

## Installation

### Quick Install

```bash
# With current AWS credentials
helm install strands-monitoring-agent ./helm \
  --namespace strands-monitoring \
  --create-namespace \
  --set aws.accessKeyId="$AWS_ACCESS_KEY_ID" \
  --set aws.roleArn="arn:aws:iam::YOUR_ACCOUNT_ID:role/KubeIntelAgentRole" \
  --set aws.sessionToken="$AWS_SESSION_TOKEN"
```

### Custom Installation

```bash
helm install strands-monitoring-agent ./helm \
  --namespace strands-monitoring \
  --create-namespace \
  --values custom-values.yaml
```

## Configuration

The following table lists the configurable parameters and their default values.

### Image Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Container image repository | `YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/strands-k8s-agent` |
| `image.tag` | Container image tag | `v2-multiarch` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |

### Application Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.logLevel` | Log level | `INFO` |
| `config.logFormat` | Log format | `json` |
| `config.kubernetesConfig` | Kubernetes config type | `in-cluster` |
| `config.maxEvents` | Maximum events to process | `100` |
| `config.maxLogLines` | Maximum log lines to collect | `100` |
| `config.analysisTimeout` | Analysis timeout in seconds | `60` |
| `config.host` | Server host | `0.0.0.0` |
| `config.port` | Server port | `8080` |

### AWS Strands Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.strands.region` | AWS region | `us-east-1` |
| `config.strands.model` | AI model to use | `amazon.titan-text-express-v1` |
| `config.strands.sessionTtl` | Session TTL in seconds | `3600` |
| `config.strands.endpoint` | Custom endpoint (optional) | `""` |

### AWS Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `aws.region` | AWS region | `us-east-1` |
| `aws.roleArn` | IAM role ARN (optional) | `""` |
| `aws.accessKeyId` | AWS access key ID | `""` |
| `aws.secretAccessKey` | AWS secret access key | `""` |
| `aws.sessionToken` | AWS session token (optional) | `""` |

### Service Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `service.type` | Service type | `LoadBalancer` |
| `service.port` | Service port | `80` |
| `service.targetPort` | Target port | `8080` |
| `service.annotations` | Service annotations | `{"service.beta.kubernetes.io/aws-load-balancer-type": "nlb"}` |

### Resource Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `resources.limits.cpu` | CPU limit | `500m` |
| `resources.limits.memory` | Memory limit | `1Gi` |
| `resources.requests.cpu` | CPU request | `100m` |
| `resources.requests.memory` | Memory request | `256Mi` |

### Security Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `serviceAccount.create` | Create service account | `true` |
| `serviceAccount.name` | Service account name | `strands-agent` |
| `rbac.create` | Create RBAC resources | `true` |
| `podSecurityContext.fsGroup` | Pod security context FS group | `1000` |
| `securityContext.runAsUser` | Container security context user ID | `1000` |
| `securityContext.runAsNonRoot` | Run as non-root | `true` |

## Examples

### Basic Deployment

```yaml
# values.yaml
aws:
  region: us-east-1
  accessKeyId: "your-access-key"
  secretAccessKey: "your-secret-key"

config:
  strands:
    model: amazon.titan-text-express-v1
```

### Production Deployment with IAM Role

```yaml
# values.yaml
aws:
  region: us-east-1
  roleArn: "arn:aws:iam::YOUR_ACCOUNT_ID:role/StrandsMonitoringRole"

service:
  type: LoadBalancer
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"

resources:
  limits:
    cpu: 1000m
    memory: 2Gi
  requests:
    cpu: 200m
    memory: 512Mi
```

### Development Deployment

```yaml
# values.yaml
service:
  type: NodePort

config:
  logLevel: DEBUG

resources:
  limits:
    cpu: 200m
    memory: 512Mi
```

## Upgrading

```bash
# Upgrade to latest version
helm upgrade strands-monitoring-agent ./helm \
  --namespace strands-monitoring

# Upgrade with new values
helm upgrade strands-monitoring-agent ./helm \
  --namespace strands-monitoring \
  --values new-values.yaml
```

## Uninstalling

```bash
helm uninstall strands-monitoring-agent --namespace strands-monitoring
```

## Troubleshooting

### Common Issues

1. **Pod not starting**: Check AWS credentials and permissions
2. **Service not accessible**: Verify LoadBalancer configuration
3. **Analysis not working**: Check Bedrock model access

### Debugging

```bash
# Check pod logs
kubectl logs -n strands-monitoring -l app=strands-monitoring-agent

# Check service status
kubectl get svc -n strands-monitoring

# Port forward for testing
kubectl port-forward -n strands-monitoring svc/strands-monitoring-agent 8080:80
```

## Current Deployment

**LoadBalancer Endpoint:**
```
http://k8s-strandsm-strandsm-f3b660183b-cc5feb7659999e33.elb.us-east-1.amazonaws.com
```

**Health Check:**
```bash
curl http://k8s-strandsm-strandsm-f3b660183b-cc5feb7659999e33.elb.us-east-1.amazonaws.com/health
```

**Analysis Test:**
```bash
curl -X POST http://k8s-strandsm-strandsm-f3b660183b-cc5feb7659999e33.elb.us-east-1.amazonaws.com/analyze \
  -H "Content-Type: application/json" \
  -d '{"scope":"cluster","analysis_request":"Analyze cluster health"}'
```

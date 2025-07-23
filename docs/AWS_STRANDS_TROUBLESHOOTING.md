# AWS Strands Troubleshooting Guide

This guide provides comprehensive troubleshooting steps for AWS Strands connectivity and configuration issues.

## 🔧 Common AWS Strands Issues

### 1. Bedrock Access Denied

**Error Messages:**
```
AccessDeniedException: User is not authorized to perform: bedrock:InvokeModel
UnauthorizedOperation: You are not authorized to perform this operation
```

**Diagnosis:**
```bash
# Check your AWS identity
aws sts get-caller-identity

# Test Bedrock access
aws bedrock list-foundation-models --region us-east-1

# Verify specific model access
aws bedrock get-foundation-model \
  --model-identifier anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --region us-east-1
```

**Solutions:**

**Option A: Add Bedrock Permissions to Existing Role/User**
```bash
# Create policy document
cat > bedrock-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:GetFoundationModel",
        "bedrock:ListFoundationModels"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-*"
      ]
    }
  ]
}
EOF

# Create and attach policy
aws iam create-policy \
  --policy-name BedrockStrandsAccess \
  --policy-document file://bedrock-policy.json

# Attach to user (replace with your username)
aws iam attach-user-policy \
  --user-name your-username \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/BedrockStrandsAccess

# Or attach to role (for EKS)
aws iam attach-role-policy \
  --role-name your-eks-role \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/BedrockStrandsAccess
```

**Option B: Use AWS Managed Policy**
```bash
# Attach AWS managed Bedrock policy (broader permissions)
aws iam attach-user-policy \
  --user-name your-username \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
```

### 2. Model Not Available

**Error Messages:**
```
ValidationException: The model identifier provided is not valid
ResourceNotFoundException: The requested model is not found
```

**Diagnosis:**
```bash
# List all available Claude models
aws bedrock list-foundation-models --region us-east-1 \
  --query 'modelSummaries[?contains(modelId, `claude`)].{ModelId:modelId,Status:modelLifecycle.status,Provider:providerName}'

# Check specific model availability
aws bedrock get-foundation-model \
  --model-identifier anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --region us-east-1
```

**Solutions:**

**Option A: Request Model Access**
1. Go to AWS Bedrock Console
2. Navigate to "Model access" in the left sidebar
3. Find "Anthropic Claude 3.5 Sonnet" and click "Request model access"
4. Fill out the use case form and submit
5. Wait for approval (usually within 24 hours)

**Option B: Use Alternative Model**
```bash
# Update configuration to use available model
export AGENT_STRANDS_MODEL="anthropic.claude-3-sonnet-20240229-v1:0"

# Or in Helm values
helm upgrade strands-monitoring-agent ./helm \
  --set config.strands.model=anthropic.claude-3-sonnet-20240229-v1:0
```

### 3. Region Availability Issues

**Error Messages:**
```
InvalidParameterValueException: The model is not available in this region
EndpointConnectionError: Could not connect to the endpoint URL
```

**Diagnosis:**
```bash
# Check Bedrock service availability by region
aws bedrock list-foundation-models --region us-east-1 | jq '.modelSummaries | length'
aws bedrock list-foundation-models --region us-west-2 | jq '.modelSummaries | length'
aws bedrock list-foundation-models --region eu-west-1 | jq '.modelSummaries | length'

# Test specific region
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query 'modelSummaries[?contains(modelId, `claude-3-5-sonnet`)].modelId'
```

**Solutions:**

**Option A: Use Supported Region**
```bash
# Update to supported region (us-east-1 recommended)
export AWS_REGION=us-east-1
export AGENT_STRANDS_REGION=us-east-1

# Update Helm deployment
helm upgrade strands-monitoring-agent ./helm \
  --set aws.region=us-east-1 \
  --set config.strands.region=us-east-1
```

**Option B: Check Regional Model Availability**
```bash
# Find regions where Claude 3.5 Sonnet is available
for region in us-east-1 us-west-2 eu-west-1 ap-southeast-1; do
  echo "Checking region: $region"
  aws bedrock list-foundation-models --region $region \
    --query 'modelSummaries[?contains(modelId, `claude-3-5-sonnet`)].modelId' \
    --output table
done
```

### 4. Rate Limiting and Quotas

**Error Messages:**
```
ThrottlingException: Rate exceeded
ServiceQuotaExceededException: The maximum number of requests has been exceeded
```

**Diagnosis:**
```bash
# Check current service quotas
aws service-quotas get-service-quota \
  --service-code bedrock \
  --quota-code L-12345678 \
  --region us-east-1

# Monitor CloudWatch metrics for throttling
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Throttles \
  --dimensions Name=ModelId,Value=anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --start-time 2025-01-07T00:00:00Z \
  --end-time 2025-01-07T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

**Solutions:**

**Option A: Request Quota Increase**
```bash
# Request quota increase via CLI
aws service-quotas request-service-quota-increase \
  --service-code bedrock \
  --quota-code L-12345678 \
  --desired-value 1000
```

**Option B: Implement Better Rate Limiting**
```yaml
# Update Helm values for better rate limiting
performance:
  queue:
    max_concurrent_requests: 2  # Reduce from 3
    rate_limit_per_minute: 30   # Reduce from 60
  strands:
    max_retries: 5
    retry_delay_base: 2
    retry_delay_max: 60
```

### 5. Authentication Issues

**Error Messages:**
```
SignatureDoesNotMatch: The request signature we calculated does not match
InvalidAccessKeyId: The AWS Access Key Id you provided does not exist
TokenRefreshRequired: The provided token has expired
```

**Diagnosis:**
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check credential source
aws configure list

# Test with specific profile
AWS_PROFILE=your-profile aws sts get-caller-identity

# Check IAM user/role permissions
aws iam get-user
aws iam list-attached-user-policies --user-name your-username
```

**Solutions:**

**Option A: Refresh Credentials**
```bash
# For temporary credentials
aws sts get-session-token --duration-seconds 3600

# For assumed role
aws sts assume-role \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/YourRole \
  --role-session-name strands-session
```

**Option B: Fix Credential Configuration**
```bash
# Reconfigure AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your-access-key
# Configure AWS CLI instead: aws configure
export AWS_SESSION_TOKEN=your-session-token  # if using temporary credentials
```

**Option C: Use IAM Role for EKS**
```yaml
# Update service account with IAM role annotation
apiVersion: v1
kind: ServiceAccount
metadata:
  name: strands-agent
  namespace: strands-monitoring
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/StrandsMonitoringRole
```

## 🔍 Diagnostic Commands

### Complete AWS Strands Health Check

```bash
#!/bin/bash
# AWS Strands Health Check Script

echo "🔍 AWS Strands Connectivity Diagnostic"
echo "======================================"

# 1. Check AWS Identity
echo "1. Checking AWS Identity..."
aws sts get-caller-identity || echo "❌ AWS credentials not configured"

# 2. Check Bedrock Service Access
echo "2. Checking Bedrock Service Access..."
aws bedrock list-foundation-models --region us-east-1 --max-items 1 > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "✅ Bedrock service accessible"
else
  echo "❌ Bedrock service not accessible"
fi

# 3. Check Claude Model Availability
echo "3. Checking Claude Model Availability..."
CLAUDE_MODELS=$(aws bedrock list-foundation-models --region us-east-1 \
  --query 'modelSummaries[?contains(modelId, `claude-3-5-sonnet`)].modelId' \
  --output text)

if [ -n "$CLAUDE_MODELS" ]; then
  echo "✅ Claude 3.5 Sonnet models available:"
  echo "$CLAUDE_MODELS"
else
  echo "❌ Claude 3.5 Sonnet models not available"
fi

# 4. Test Model Invocation
echo "4. Testing Model Invocation..."
aws bedrock invoke-model \
  --region us-east-1 \
  --model-id anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --body '{"messages":[{"role":"user","content":"Hello"}],"max_tokens":10}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/bedrock-test.json > /dev/null 2>&1

if [ $? -eq 0 ]; then
  echo "✅ Model invocation successful"
  rm -f /tmp/bedrock-test.json
else
  echo "❌ Model invocation failed"
fi

# 5. Check Rate Limits
echo "5. Checking Recent Rate Limits..."
THROTTLES=$(aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Throttles \
  --dimensions Name=ModelId,Value=anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 \
  --statistics Sum \
  --query 'Datapoints[0].Sum' \
  --output text 2>/dev/null)

if [ "$THROTTLES" = "None" ] || [ -z "$THROTTLES" ]; then
  echo "✅ No recent throttling detected"
else
  echo "⚠️ Throttling detected: $THROTTLES requests throttled in last hour"
fi

echo "======================================"
echo "Diagnostic complete"
```

### Agent-Specific Diagnostics

```bash
# Check agent health
curl -s http://your-endpoint/health | jq '.'

# Test Strands connectivity from within pod
kubectl exec -n strands-monitoring deployment/strands-monitoring-agent -- \
  python -c "
import asyncio
from src.agent.strands_agent_enhanced import KubernetesMonitoringAgent
from src.k8s.collector import DataCollector
from src.k8s.client import KubernetesClient

async def test():
    try:
        client = KubernetesClient()
        collector = DataCollector(client)
        agent = KubernetesMonitoringAgent(collector)
        health = await agent.health_check()
        print(f'✅ Agent health: {health[\"healthy\"]}')
        print(f'🤖 Strands agent: {health[\"components\"][\"strands_agent\"]}')
        print(f'🔗 State session: {health[\"components\"][\"state_session\"]}')
    except Exception as e:
        print(f'❌ Error: {e}')

asyncio.run(test())
"

# Check AWS credentials in pod
kubectl exec -n strands-monitoring deployment/strands-monitoring-agent -- env | grep AWS

# Test Bedrock access from pod
kubectl exec -n strands-monitoring deployment/strands-monitoring-agent -- \
  aws bedrock list-foundation-models --region us-east-1 --max-items 1
```

## 🚨 Emergency Recovery

### When Strands is Completely Unavailable

The agent includes fallback mechanisms for when AWS Strands is unavailable:

```bash
# Check fallback status
curl -s http://your-endpoint/health | jq '.components.fallback_analyzer'

# Force fallback mode (for testing)
kubectl set env deployment/strands-monitoring-agent -n strands-monitoring \
  AGENT_ENABLE_FALLBACK_ANALYSIS=true \
  AGENT_STRANDS_TIMEOUT=5

# Test fallback analysis
curl -X POST http://your-endpoint/analyze \
  -H "Content-Type: application/json" \
  -d '{"scope": "cluster", "analysis_request": "Check cluster health", "force_fallback": true}'
```

### Rollback Procedures

```bash
# Rollback to previous working version
helm rollback strands-monitoring-agent -n strands-monitoring

# Or redeploy with known working configuration
helm upgrade strands-monitoring-agent ./helm \
  --values helm/values-working-backup.yaml \
  --force

# Check rollback status
kubectl rollout status deployment/strands-monitoring-agent -n strands-monitoring
```

## 📊 Monitoring and Alerting

### CloudWatch Metrics to Monitor

```bash
# Set up CloudWatch alarms for Bedrock
aws cloudwatch put-metric-alarm \
  --alarm-name "BedrockThrottling" \
  --alarm-description "Bedrock API throttling detected" \
  --metric-name Throttles \
  --namespace AWS/Bedrock \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ModelId,Value=anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --evaluation-periods 2

# Monitor invocation errors
aws cloudwatch put-metric-alarm \
  --alarm-name "BedrockErrors" \
  --alarm-description "Bedrock API errors detected" \
  --metric-name InvocationErrors \
  --namespace AWS/Bedrock \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ModelId,Value=anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --evaluation-periods 1
```

### Application Metrics

```bash
# Monitor agent performance
curl -s http://your-endpoint/performance/stats | jq '.'

# Check error rates
curl -s http://your-endpoint/performance/errors | jq '.error_rate_24h'

# Monitor cache hit rates
curl -s http://your-endpoint/performance/cache | jq '.hit_rate'
```

## 🔧 Configuration Optimization

### Optimal Settings for Different Scenarios

**High-Volume Production:**
```yaml
config:
  strands:
    timeout: 45
    max_retries: 5
    temperature: 0.1
    max_tokens: 3000
performance:
  queue:
    max_concurrent_requests: 2
    rate_limit_per_minute: 30
  cache:
    max_size: 2000
    default_ttl: 600
```

**Development/Testing:**
```yaml
config:
  strands:
    timeout: 15
    max_retries: 2
    temperature: 0.2
    max_tokens: 2000
performance:
  queue:
    max_concurrent_requests: 1
    rate_limit_per_minute: 10
  cache:
    max_size: 500
    default_ttl: 300
```

**Cost-Optimized:**
```yaml
config:
  strands:
    timeout: 30
    max_retries: 3
    temperature: 0.1
    max_tokens: 1500  # Reduce token usage
performance:
  queue:
    max_concurrent_requests: 1
    rate_limit_per_minute: 20
  cache:
    max_size: 1500
    default_ttl: 900  # Longer cache retention
```

This troubleshooting guide should help resolve most AWS Strands connectivity and configuration issues. For additional support, check the main README troubleshooting section and ensure all prerequisites are met.
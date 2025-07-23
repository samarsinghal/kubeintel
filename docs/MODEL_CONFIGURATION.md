# AWS Strands Model Configuration

This document explains how the AWS Strands Monitoring Agent is configured to access and use AI models.

## Current Model Configuration

### Default Model
- **Model**: `claude-3-sonnet`
- **Provider**: AWS Bedrock (via AWS Strands)
- **Region**: `us-west-2`
- **Temperature**: `0.1` (low for consistent analysis)
- **Max Tokens**: `4000`

### Configuration Sources

The agent loads model configuration from multiple sources in this priority order:

1. **Environment Variables**
   ```bash
   AGENT_STRANDS_MODEL=claude-3-sonnet
   AGENT_STRANDS_REGION=us-west-2
   AGENT_STRANDS_ENDPOINT=https://custom-endpoint.com  # Optional
   AGENT_STRANDS_SESSION_TTL=3600
   ```

2. **Helm Values**
   ```yaml
   config:
     strands:
       model: claude-3-sonnet
       region: us-west-2
       endpoint: ""  # Optional custom endpoint
       sessionTtl: 3600
   ```

3. **Configuration File** (src/config.py defaults)

## How the Agent Accesses the Model

### 1. AWS Strands SDK Integration

The agent uses the AWS Strands SDK which handles:
- Model authentication via AWS credentials
- Request routing to the appropriate model endpoint
- Response parsing and error handling
- State session management

```python
# Agent initialization with model config
agent = KubernetesMonitoringAgent(
    data_collector=data_collector,
    state_session=state_session,
    mcp_manager=mcp_manager,
    strands_config={
        "model": "claude-3-sonnet",
        "region": "us-west-2",
        "temperature": 0.1,
        "max_tokens": 4000
    }
)
```

### 2. AWS Authentication

The agent requires AWS credentials to access the model. Multiple authentication methods are supported:

#### Option A: IAM Roles for Service Accounts (IRSA) - Recommended for EKS
```yaml
# In Helm values
aws:
  roleArn: "arn:aws:iam::123456789012:role/StrandsAgentRole"
```

#### Option B: Environment Variables
```bash
AWS_ACCESS_KEY_ID=your-access-key
# Use IRSA or AWS CLI configuration
AWS_SESSION_TOKEN=your-session-token  # If using temporary credentials
AWS_REGION=us-west-2
```

#### Option C: AWS Profile
```bash
AWS_PROFILE=strands-agent-profile
```

#### Option D: Instance Profile (for EC2-based clusters)
Automatically uses the instance's IAM role.

### 3. Required AWS Permissions

The agent needs the following AWS permissions:

```json
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
        "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-sonnet-*",
        "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-haiku-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "strands:*"
      ],
      "Resource": "*"
    }
  ]
}
```

## Supported Models

The agent can be configured to use different models:

### Anthropic Claude Models (via AWS Bedrock)
- `claude-3-sonnet` (default) - Balanced performance and cost
- `claude-3-haiku` - Faster, lower cost
- `claude-3-opus` - Highest capability

### Configuration Examples

#### High Performance Setup
```yaml
config:
  strands:
    model: claude-3-opus
    region: us-west-2
```

#### Cost-Optimized Setup
```yaml
config:
  strands:
    model: claude-3-haiku
    region: us-west-2
```

#### Custom Endpoint
```yaml
config:
  strands:
    model: claude-3-sonnet
    region: us-west-2
    endpoint: https://your-custom-strands-endpoint.com
```

## Model Usage in Analysis

### Analysis Prompt Structure

The agent sends structured prompts to the model:

```
You are a Kubernetes monitoring expert with access to comprehensive AWS EKS cluster analysis tools.

Use the eks_cluster_analyzer tool to collect detailed cluster data.

The tool provides comprehensive information including:
- Pod status, health, and resource usage
- Service configurations and endpoints
- Deployment status and replica counts
- Recent events and their patterns
- Node information and cluster health

After collecting the data, analyze it for:
1. Pod Health Issues: Failed pods, high restart counts, resource constraints
2. Service Configuration: Misconfigured services, endpoint issues
3. Deployment Status: Failed deployments, scaling issues
4. Resource Utilization: CPU/memory constraints, resource quotas
5. Events Analysis: Error patterns, warning trends, system events
6. Security & Best Practices: Configuration issues, security concerns

Provide your analysis in this structured format:
- Status: Overall cluster health (Healthy/Warning/Critical)
- Critical Issues: Immediate problems requiring attention
- Warnings: Issues that should be monitored
- Recommendations: Specific actionable steps
- Summary: Brief overview of cluster state
```

### Response Processing

The agent processes the model's response to extract:
- **Findings**: Structured list of issues with severity levels
- **Recommendations**: Actionable steps to resolve problems
- **Summary**: Brief overview of cluster health

## Troubleshooting Model Access

### Common Issues

1. **Authentication Errors**
   ```
   Error: Unable to locate credentials
   ```
   **Solution**: Ensure AWS credentials are properly configured

2. **Model Access Denied**
   ```
   Error: User is not authorized to perform: bedrock:InvokeModel
   ```
   **Solution**: Add required Bedrock permissions to IAM role/user

3. **Region Mismatch**
   ```
   Error: Model not available in region
   ```
   **Solution**: Ensure the model is available in your configured region

4. **Rate Limiting**
   ```
   Error: ThrottlingException
   ```
   **Solution**: Implement retry logic or reduce request frequency

### Debugging Steps

1. **Check AWS Credentials**
   ```bash
   kubectl exec -it deployment/strands-monitoring-agent -- aws sts get-caller-identity
   ```

2. **Verify Model Access**
   ```bash
   kubectl exec -it deployment/strands-monitoring-agent -- aws bedrock list-foundation-models --region us-west-2
   ```

3. **Check Agent Logs**
   ```bash
   kubectl logs -f deployment/strands-monitoring-agent
   ```

4. **Test Health Endpoint**
   ```bash
   curl http://strands-agent/health
   ```

## Performance Considerations

### Model Selection Impact

| Model | Speed | Cost | Quality | Use Case |
|-------|-------|------|---------|----------|
| claude-3-haiku | Fast | Low | Good | Frequent monitoring |
| claude-3-sonnet | Medium | Medium | High | Balanced (default) |
| claude-3-opus | Slow | High | Highest | Critical analysis |

### Optimization Settings

```yaml
config:
  strands:
    model: claude-3-sonnet
    temperature: 0.1  # Low for consistent analysis
    maxTokens: 4000   # Sufficient for detailed analysis
    timeout: 30       # Request timeout in seconds
```

## Security Best Practices

1. **Use IRSA for EKS deployments**
2. **Rotate AWS credentials regularly**
3. **Use least-privilege IAM policies**
4. **Enable CloudTrail logging for model usage**
5. **Monitor costs and usage patterns**

## Cost Management

### Monitoring Usage
- Enable AWS Cost Explorer for Bedrock usage
- Set up billing alerts for unexpected usage
- Monitor token consumption in agent logs

### Cost Optimization
- Use `claude-3-haiku` for frequent, simple analyses
- Implement caching for repeated analyses
- Set appropriate timeout values
- Use namespace-scoped analysis when possible
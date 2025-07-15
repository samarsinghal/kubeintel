# KubeIntel Helm Chart Upgrade Guide

This guide covers upgrading KubeIntel Helm deployments to support Claude 3.5 models.

## Overview

The KubeIntel Helm chart now supports:
- **Claude 3.5 Sonnet** as the primary model for enhanced analysis quality
- **Claude 3.5 Haiku** as an optimized fallback model for reliability
- **Configurable settings** for all timeouts, limits, and operational parameters
- **Automatic configuration validation** before deployment
- **Migration utilities** for smooth upgrades

## Current Model Configuration

### Default Models (Recommended)
- **Primary**: `us.anthropic.claude-3-5-sonnet-20241022-v2:0`
- **Fallback**: `us.anthropic.claude-3-5-haiku-20241022-v1:0`

### Legacy Support
- **Legacy Mode**: `anthropic.claude-3-haiku-20240307-v1:0` (Claude 3 Haiku)

## Upgrade Paths

### From Claude 3 Haiku to Claude 3.5 (Recommended)

This is the recommended upgrade path for better analysis quality and reliability.

#### Step 1: Backup Current Configuration

```bash
# Backup current Helm values
helm get values kubeintel -n kubeintel > kubeintel-values-backup.yaml

# Backup current deployment
kubectl get deployment kubeintel -n kubeintel -o yaml > kubeintel-deployment-backup.yaml
```

#### Step 2: Update to Current Configuration

```bash
helm upgrade kubeintel ./helm \
  --namespace kubeintel \
  --set config.strands.model=us.anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --set config.strands.fallbackModel=us.anthropic.claude-3-5-haiku-20241022-v1:0 \
  --set config.strands.region=us-east-1
```

Update your `values.yaml` or create an override file:

```yaml
# values-claude35.yaml
config:
  strands:
    # Enable Claude 3.5 mode (default)
    legacyMode: false
    
    # Primary model for analysis
    model: anthropic.claude-3-5-sonnet-20241022-v2:0
    
    # Fallback model for reliability
    fallbackModel: anthropic.claude-3-5-haiku-20241022-v1:0
    
    # Optimized session TTL for Claude 3.5
    sessionTtl: 7200
    
    # Required for Claude 3.5 stability
    disableStreaming: true
    
    # Enhanced performance settings
    performance:
      enhancedPrompts: true
      prioritizeQuality: true
      contextOptimization: true

# Recommended resource adjustments for Claude 3.5
resources:
  limits:
    memory: 2Gi
    cpu: 1000m
  requests:
    memory: 512Mi
    cpu: 200m

# Enable configuration validation
validation:
  enabled: true
```

#### Step 3: Validate Configuration

```bash
# Validate the new configuration
python scripts/validate-claude35-config.py --helm-values values-claude35.yaml

# Check what would change
helm diff upgrade kubeintel ./helm -f values-claude35.yaml
```

#### Step 4: Perform Upgrade

```bash
# Upgrade to Claude 3.5
helm upgrade kubeintel ./helm -f values-claude35.yaml

# Monitor the rollout
kubectl rollout status deployment/kubeintel -n default

# Verify the upgrade
kubectl logs -n default -l app.kubernetes.io/name=kubeintel --tail=50
```

### Gradual Migration (For Production)

For production environments, use a gradual migration approach:

#### Step 1: Enable Migration Mode

```yaml
# values-migration.yaml
migration:
  enabled: true
  strategy:
    type: gradual
    claude35Percentage: 25  # Start with 25% traffic

config:
  strands:
    legacyMode: false
    model: anthropic.claude-3-5-sonnet-20241022-v2:0
    fallbackModel: anthropic.claude-3-haiku-20240307-v1:0  # Keep legacy fallback initially
```

#### Step 2: Gradual Rollout

```bash
# Deploy with 25% Claude 3.5 traffic
helm upgrade kubeintel ./helm -f values-migration.yaml

# Monitor performance and gradually increase
helm upgrade kubeintel ./helm --set migration.strategy.claude35Percentage=50
helm upgrade kubeintel ./helm --set migration.strategy.claude35Percentage=75
helm upgrade kubeintel ./helm --set migration.strategy.claude35Percentage=100

# Finally, update fallback to Claude 3.5 Haiku
helm upgrade kubeintel ./helm --set config.strands.fallbackModel=anthropic.claude-3-5-haiku-20241022-v1:0
```

### Legacy Mode (Backward Compatibility)

To maintain Claude 3 Haiku compatibility:

```yaml
# values-legacy.yaml
config:
  strands:
    # Enable legacy mode
    legacyMode: true
    
    # Use Claude 3 Haiku
    legacyModel: anthropic.claude-3-haiku-20240307-v1:0
    
    # Legacy session TTL
    sessionTtl: 3600
```

```bash
helm upgrade kubeintel ./helm -f values-legacy.yaml
```

## Configuration Options

### Model Selection

```yaml
config:
  strands:
    # Claude 3.5 mode (recommended)
    legacyMode: false
    model: anthropic.claude-3-5-sonnet-20241022-v2:0
    fallbackModel: anthropic.claude-3-5-haiku-20241022-v1:0
    
    # OR Legacy mode (backward compatibility)
    legacyMode: true
    legacyModel: anthropic.claude-3-haiku-20240307-v1:0
```

### Performance Tuning

```yaml
config:
  strands:
    # Session configuration
    sessionTtl: 7200  # 2 hours for Claude 3.5
    
    # Connection timeouts
    connectTimeout: 30
    readTimeout: 60
    
    # Fallback configuration
    fallback:
      enabled: true
      maxAttempts: 3
      retryDelay: 5
    
    # Performance optimization
    performance:
      enhancedPrompts: true      # Use Claude 3.5 optimized prompts
      prioritizeQuality: true    # Favor quality over speed
      contextOptimization: true  # Optimize context handling
```

### Resource Configuration

```yaml
# Recommended resources for Claude 3.5
resources:
  limits:
    memory: 2Gi    # Increased for Claude 3.5
    cpu: 1000m     # More CPU for enhanced reasoning
  requests:
    memory: 512Mi  # Higher baseline
    cpu: 200m

# For high-throughput environments
resources:
  limits:
    memory: 4Gi
    cpu: 2000m
  requests:
    memory: 1Gi
    cpu: 500m
```

### Validation and Migration

```yaml
# Enable pre-deployment validation
validation:
  enabled: true

# Enable migration helpers
migration:
  enabled: true
  createBackup: true
  strategy:
    type: gradual  # or "immediate"
    claude35Percentage: 100
```

## Troubleshooting

### Common Issues

#### 1. Pod Fails to Start After Upgrade

```bash
# Check pod status
kubectl get pods -n default -l app.kubernetes.io/name=kubeintel

# Check events
kubectl describe pod -n default -l app.kubernetes.io/name=kubeintel

# Check logs
kubectl logs -n default -l app.kubernetes.io/name=kubeintel
```

**Common causes:**
- Insufficient memory/CPU resources
- Invalid model configuration
- AWS IAM permission issues

#### 2. Model Not Available Error

```bash
# Check AWS region and model availability
aws bedrock list-foundation-models --region us-west-2 | grep claude-3-5

# Verify IAM permissions
aws bedrock invoke-model --model-id anthropic.claude-3-5-sonnet-20241022-v2:0 --body '{"messages":[{"role":"user","content":"test"}],"max_tokens":10}' --region us-west-2
```

#### 3. Configuration Validation Failures

```bash
# Run detailed validation
python scripts/validate-claude35-config.py --helm-values values.yaml --strict

# Check configuration warnings in pod annotations
kubectl get pod -n default -l app.kubernetes.io/name=kubeintel -o jsonpath='{.items[0].metadata.annotations.kubeintel\.io/config-warnings}'
```

### Rollback Procedures

#### Quick Rollback with Helm

```bash
# Rollback to previous release
helm rollback kubeintel

# Or rollback to specific revision
helm history kubeintel
helm rollback kubeintel 2
```

#### Rollback with Scripts

```bash
# Use the automated rollback script
./scripts/rollback-claude35.sh

# Or rollback only Helm deployment
./scripts/rollback-claude35.sh --helm-only
```

#### Manual Rollback

```bash
# Restore from backup
kubectl apply -f kubeintel-deployment-backup.yaml

# Or update values to legacy mode
helm upgrade kubeintel ./helm --set config.strands.legacyMode=true
```

## Monitoring and Validation

### Post-Upgrade Checks

```bash
# 1. Verify deployment is running
kubectl get deployment kubeintel -n default

# 2. Check pod status
kubectl get pods -n default -l app.kubernetes.io/name=kubeintel

# 3. Verify model configuration
kubectl get configmap kubeintel-config -n default -o yaml | grep -E "(model|claude)"

# 4. Test functionality
curl -X POST http://your-kubeintel-service/analyze -d '{"query":"cluster status"}'

# 5. Monitor logs for Claude 3.5 usage
kubectl logs -n default -l app.kubernetes.io/name=kubeintel --tail=100 | grep -i claude
```

### Performance Monitoring

```bash
# Monitor resource usage
kubectl top pods -n default -l app.kubernetes.io/name=kubeintel

# Check response times
kubectl logs -n default -l app.kubernetes.io/name=kubeintel | grep -E "(response_time|duration)"

# Monitor fallback usage
kubectl logs -n default -l app.kubernetes.io/name=kubeintel | grep -i fallback
```

## Best Practices

### 1. Test in Non-Production First

Always test the upgrade in a development or staging environment:

```bash
# Deploy to staging namespace
helm install kubeintel-staging ./helm -f values-claude35.yaml -n staging --create-namespace

# Run integration tests
python tests/test_integration_model_fallback.py

# Validate performance
python tests/test_claude35_performance_comparison.py
```

### 2. Monitor Resource Usage

Claude 3.5 may require more resources:

```bash
# Set appropriate resource limits
helm upgrade kubeintel ./helm --set resources.limits.memory=2Gi --set resources.limits.cpu=1000m

# Enable horizontal pod autoscaling if needed
kubectl autoscale deployment kubeintel --cpu-percent=70 --min=1 --max=5
```

### 3. Use IAM Roles

Avoid hardcoded credentials:

```yaml
aws:
  roleArn: "arn:aws:iam::YOUR_ACCOUNT:role/KubeIntelClaude35Role"
  # Don't set accessKeyId/secretAccessKey
```

### 4. Enable Monitoring

Set up monitoring for the upgraded deployment:

```yaml
# Add monitoring annotations
podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

## Migration Checklist

- [ ] Backup current configuration and deployment
- [ ] Validate new configuration with validation script
- [ ] Test upgrade in non-production environment
- [ ] Verify AWS IAM permissions for Claude 3.5 models
- [ ] Update resource limits for Claude 3.5 requirements
- [ ] Plan rollback procedure
- [ ] Perform upgrade during maintenance window
- [ ] Verify deployment status and functionality
- [ ] Monitor performance and resource usage
- [ ] Update monitoring and alerting rules
- [ ] Document any configuration changes
- [ ] Clean up backup files after successful upgrade

## Support

For issues during upgrade:

1. Check the troubleshooting section above
2. Run configuration validation: `python scripts/validate-claude35-config.py`
3. Review Helm release history: `helm history kubeintel`
4. Check pod logs: `kubectl logs -n default -l app.kubernetes.io/name=kubeintel`
5. Use rollback procedures if needed

For additional help, refer to:
- Migration utilities: `scripts/README.md`
- Configuration validation: `python scripts/validate-claude35-config.py --help`
- Rollback procedures: `./scripts/rollback-claude35.sh --help`
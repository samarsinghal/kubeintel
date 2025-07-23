# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.2.x   | :white_check_mark: |
| 1.1.x   | :white_check_mark: |
| < 1.1   | :x:                |

## Reporting a Vulnerability

Please report security vulnerabilities by emailing [security@kubeintel.io](mailto:security@kubeintel.io).

**Please do not report security vulnerabilities through public GitHub issues.**

We will acknowledge your email within 48 hours and provide a detailed response within 72 hours indicating the next steps in handling your report.

## Security Best Practices

When deploying KubeIntel:

1. **Use IRSA**: Always use IAM Roles for Service Accounts instead of static credentials
2. **Least Privilege**: Grant only the minimum required permissions
3. **Network Security**: Use network policies to restrict traffic
4. **Regular Updates**: Keep the application and dependencies updated
5. **Monitoring**: Monitor for unusual activity and access patterns

## Security Features

- **No Static Credentials**: Uses temporary AWS credentials via IRSA
- **Container Security**: Runs as non-root user with read-only filesystem
- **Network Isolation**: Supports Kubernetes network policies
- **Audit Logging**: All API calls are logged for audit purposes

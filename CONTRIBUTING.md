# Contributing to KubeIntel

We welcome contributions to KubeIntel! This document outlines the process for contributing to the project.

## How to Contribute

### Reporting Issues

When reporting issues, please include:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Kubernetes version, AWS region)
- Screenshots if applicable

### Pull Requests

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for your changes
5. Ensure tests pass (`python -m pytest tests/ -v`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Development Setup

### Prerequisites
- Python 3.12+
- Docker
- kubectl
- Helm 3.x
- AWS CLI with Bedrock access

### Local Development
```bash
# Clone repository
git clone https://github.com/yourusername/kubeintel.git
cd kubeintel

# Set up Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up configuration
cp .env.example .env
# Edit .env with your settings

# Run tests
python -m pytest tests/ -v
```

## Code Guidelines

### Style
- Follow PEP 8
- Use type hints
- Add docstrings to functions and classes
- Keep functions focused and concise

### Commit Messages
```
feat: Add pod failure prediction

- Implement prediction algorithm
- Add confidence scoring
- Update API endpoints
- Add tests

Fixes #123
```

### Testing
- Write tests for new functionality
- Test both success and failure cases
- Include integration tests where needed
- Maintain or improve coverage

## Areas for Contribution
- AI model integration
- Kubernetes feature support
- Monitoring capabilities
- Documentation improvements
- Performance optimization
- Test coverage

## Getting Help
- Check [GitHub Issues](https://github.com/yourusername/kubeintel/issues)
- Start a [Discussion](https://github.com/yourusername/kubeintel/discussions)
- Review the [README.md](README.md)

## License
By contributing, you agree that your contributions will be licensed under the MIT License.

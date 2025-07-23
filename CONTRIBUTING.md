# Contributing to KubeIntel

Thank you for your interest in contributing to KubeIntel! We welcome contributions from the community and are pleased to have you join us.

## 🤝 Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## 🚀 How to Contribute

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When you create a bug report, please include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples to demonstrate the steps**
- **Describe the behavior you observed and what behavior you expected**
- **Include screenshots if applicable**
- **Include your environment details** (OS, Kubernetes version, AWS region, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- **Use a clear and descriptive title**
- **Provide a step-by-step description of the suggested enhancement**
- **Provide specific examples to demonstrate the enhancement**
- **Describe the current behavior and explain the behavior you expected**
- **Explain why this enhancement would be useful**

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following our coding standards
3. **Add tests** for your changes if applicable
4. **Ensure all tests pass**
5. **Update documentation** as needed
6. **Create a pull request** with a clear title and description

## 🛠️ Development Setup

### Prerequisites

- Python 3.12+
- Docker
- kubectl
- Helm 3.x
- AWS CLI configured
- Access to AWS Bedrock

### Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/kubeintel.git
   cd kubeintel
   ```

2. **Set up Python environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run tests:**
   ```bash
   python -m pytest tests/ -v
   ```

5. **Build and test locally:**
   ```bash
   docker build -t kubeintel:dev .
   ```

### Testing

We use pytest for testing. Please ensure all tests pass before submitting a PR:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_kubernetes_tools.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions small and focused
- Use type hints where appropriate

### Commit Messages

Please use clear and meaningful commit messages:

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

Example:
```
Add predictive analytics for pod failures

- Implement anomaly detection algorithm
- Add prediction confidence scoring
- Update API to include prediction endpoints
- Add tests for prediction accuracy

Fixes #123
```

## 📝 Documentation

- Update README.md if you change functionality
- Add docstrings to new functions and classes
- Update API documentation for new endpoints
- Include examples in documentation

## 🧪 Testing Guidelines

### Unit Tests

- Write tests for all new functionality
- Maintain or improve test coverage
- Use descriptive test names
- Test both success and failure cases

### Integration Tests

- Test end-to-end functionality
- Test with real Kubernetes clusters when possible
- Mock external dependencies appropriately

### Test Structure

```python
def test_function_name_should_expected_behavior():
    # Arrange
    setup_test_data()
    
    # Act
    result = function_under_test()
    
    # Assert
    assert result == expected_value
```

## 🏗️ Architecture Guidelines

### Code Organization

- Keep related functionality together
- Use clear module boundaries
- Separate concerns (API, business logic, data access)
- Follow the existing project structure

### Error Handling

- Use appropriate exception types
- Provide meaningful error messages
- Log errors appropriately
- Handle edge cases gracefully

### Performance

- Consider performance implications of changes
- Use appropriate data structures
- Avoid unnecessary API calls
- Cache when appropriate

## 🔍 Review Process

1. **Automated checks** must pass (tests, linting, security scans)
2. **Code review** by at least one maintainer
3. **Documentation review** if applicable
4. **Testing** in a development environment
5. **Approval** and merge by maintainer

## 🎯 Areas for Contribution

We especially welcome contributions in these areas:

- **New AI Models**: Support for additional Bedrock models
- **Kubernetes Features**: Support for new Kubernetes resources
- **Monitoring**: Additional metrics and alerting
- **UI/UX**: Improvements to the web interface
- **Documentation**: Examples, tutorials, and guides
- **Testing**: Additional test coverage
- **Performance**: Optimization and efficiency improvements

## 📞 Getting Help

If you need help with contributing:

- Check existing [GitHub Issues](https://github.com/yourusername/kubeintel/issues)
- Start a [GitHub Discussion](https://github.com/yourusername/kubeintel/discussions)
- Review the [documentation](README.md)

## 🏷️ Issue Labels

We use these labels to categorize issues:

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Improvements or additions to documentation
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention is needed
- `question`: Further information is requested

## 🎉 Recognition

Contributors will be recognized in:

- README.md acknowledgments
- Release notes for significant contributions
- GitHub contributor statistics

Thank you for contributing to KubeIntel! 🚀

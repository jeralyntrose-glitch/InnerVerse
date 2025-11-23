# Contributing to InnerVerse

Thank you for your interest in contributing to InnerVerse! This document provides guidelines and instructions for contributing.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

## 🤝 Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Keep discussions professional

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Git
- Docker (optional, but recommended)

### Setup Development Environment

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/InnerVerse.git
   cd InnerVerse
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Setup pre-commit hooks** (optional but recommended)
   ```bash
   pre-commit install
   ```

5. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

6. **Setup database**
   ```bash
   # Create database
   createdb innerverse_dev
   
   # Run migrations
   alembic upgrade head
   ```

## 🔄 Development Workflow

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation changes
- `refactor/description` - Code refactoring
- `test/description` - Test improvements

### Commit Messages

Follow conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting, no code change
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance

**Examples:**
```
feat(api): add knowledge graph export endpoint
fix(database): resolve connection pool leak
docs(readme): update installation instructions
refactor(routes): extract common dependencies
test(services): add tests for chat service
```

## 📝 Coding Standards

### Python Style Guide

We follow PEP 8 with some modifications:

- **Line length**: 100 characters
- **Quotes**: Use double quotes for strings
- **Type hints**: Required for all function signatures
- **Docstrings**: Required for all public functions/classes

### Code Formatting

We use automated formatters:

```bash
# Format code
black .

# Sort imports
isort .

# Lint
ruff check .

# Type check
mypy src/
```

### Code Structure

```python
"""
Module docstring explaining purpose
"""
import standard_library
import third_party_packages

from local_modules import something

# Constants
CONSTANT_VALUE = 42

# Classes and functions with type hints
def function_name(param: str, count: int = 0) -> dict:
    """
    Function docstring
    
    Args:
        param: Description
        count: Description
        
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: When this happens
    """
    pass
```

### Type Hints

Always use type hints:

```python
from typing import List, Dict, Optional, Union

def process_data(
    items: List[str],
    config: Dict[str, Any],
    timeout: Optional[int] = None
) -> Union[Dict, None]:
    ...
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api/test_health.py

# Run specific test
pytest tests/test_api/test_health.py::test_health_check

# Run with verbose output
pytest -v

# Run and stop at first failure
pytest -x
```

### Writing Tests

- Place tests in `tests/` directory
- Mirror the source structure
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)

```python
def test_feature_behavior():
    """Test that feature behaves correctly"""
    # Arrange
    input_data = {"key": "value"}
    
    # Act
    result = process_function(input_data)
    
    # Assert
    assert result["status"] == "success"
    assert "data" in result
```

### Test Coverage

- Aim for 80%+ coverage
- All new features must include tests
- Bug fixes should include regression tests

## 🔀 Pull Request Process

### Before Submitting

1. **Update from main**
   ```bash
   git checkout main
   git pull origin main
   git checkout your-branch
   git rebase main
   ```

2. **Run all checks**
   ```bash
   black .
   ruff check .
   mypy src/
   pytest
   ```

3. **Update documentation** if needed

4. **Update CHANGELOG.md** (if applicable)

### Creating Pull Request

1. **Push your branch**
   ```bash
   git push origin your-branch
   ```

2. **Create PR** on GitHub
   - Use the PR template
   - Link related issues
   - Add screenshots if UI changes
   - Request reviewers

3. **Respond to feedback**
   - Address all comments
   - Push additional commits if needed
   - Request re-review when ready

### PR Requirements

- [ ] All tests pass
- [ ] Code coverage maintained or improved
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (for user-facing changes)
- [ ] No merge conflicts
- [ ] Approved by at least one maintainer

## 🐛 Reporting Bugs

### Before Reporting

1. Check existing issues
2. Try latest version
3. Verify it's reproducible

### Bug Report Template

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened.

**Screenshots**
If applicable, add screenshots.

**Environment:**
- OS: [e.g. macOS 13.0]
- Python version: [e.g. 3.11.5]
- InnerVerse version: [e.g. 1.0.0]

**Additional context**
Any other relevant information.
```

## 💡 Suggesting Features

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
What you want to happen.

**Describe alternatives you've considered**
Other solutions you've thought about.

**Additional context**
Any other relevant information, mockups, etc.
```

## 📚 Additional Resources

- [API Documentation](http://localhost:5000/docs)
- [Architecture Overview](docs/architecture.md) (if exists)
- [Development Guide](docs/development.md) (if exists)

## 🎓 Learning Resources

If you're new to any of the technologies:

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Tutorial](https://www.postgresqltutorial.com/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Pytest Documentation](https://docs.pytest.org/)

## 📞 Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue
- **Chat**: [Your chat platform if you have one]

## 🙏 Thank You!

Your contributions make InnerVerse better for everyone. We appreciate your time and effort!


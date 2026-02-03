# Contributing to SalesBoost

First off, thank you for considering contributing to SalesBoost! It's people like you that make SalesBoost such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* **Use a clear and descriptive title**
* **Describe the exact steps which reproduce the problem**
* **Provide specific examples to demonstrate the steps**
* **Describe the behavior you observed after following the steps**
* **Explain which behavior you expected to see instead and why**
* **Include screenshots and animated GIFs if possible**

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* **Use a clear and descriptive title**
* **Provide a step-by-step description of the suggested enhancement**
* **Provide specific examples to demonstrate the steps**
* **Describe the current behavior and explain which behavior you expected to see instead**
* **Explain why this enhancement would be useful**

### Pull Requests

* Fill in the required template
* Do not include issue numbers in the PR title
* Follow the Python and TypeScript styleguides
* Include thoughtfully-worded, well-structured tests
* Document new code
* End all files with a newline

## Development Setup

### Prerequisites

* Python 3.11+
* Node.js 18+
* PostgreSQL (for production) or SQLite (for development)

### Setup Steps

```bash
# Clone the repository
git clone https://github.com/yourusername/salesboost.git
cd salesboost

# Backend setup
pip install -r config/python/requirements.txt
python scripts/deployment/init_database.py

# Frontend setup
cd frontend
npm install
cd ..

# Run tests
pytest tests/
```

## Styleguides

### Git Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line
* Consider starting the commit message with an applicable emoji:
    * 🎨 `:art:` when improving the format/structure of the code
    * 🐎 `:racehorse:` when improving performance
    * 📝 `:memo:` when writing docs
    * 🐛 `:bug:` when fixing a bug
    * 🔥 `:fire:` when removing code or files
    * ✅ `:white_check_mark:` when adding tests
    * 🔒 `:lock:` when dealing with security

### Python Styleguide

* Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
* Use type hints for function parameters and return values
* Write docstrings for all public modules, functions, classes, and methods
* Maximum line length is 100 characters

### TypeScript Styleguide

* Follow the [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
* Use TypeScript for all new code
* Prefer functional components with hooks over class components
* Use meaningful variable names

### Documentation Styleguide

* Use [Markdown](https://daringfireball.net/projects/markdown/)
* Reference functions and classes in backticks: \`functionName()\`
* Include code examples where appropriate

## Project Structure

```
SalesBoost/
├── app/              # Core multi-agent system
├── frontend/         # React frontend
├── scripts/          # Utility scripts
├── tests/            # Test suite
├── docs/             # Documentation
└── config/           # Configuration files
```

## Testing

* Write tests for all new features
* Ensure all tests pass before submitting PR
* Aim for >80% code coverage

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_agent.py

# Run with coverage
pytest --cov=app tests/
```

## Additional Notes

### Issue and Pull Request Labels

* `bug` - Something isn't working
* `enhancement` - New feature or request
* `documentation` - Improvements or additions to documentation
* `good first issue` - Good for newcomers
* `help wanted` - Extra attention is needed

## Questions?

Feel free to open an issue with your question or reach out to the maintainers directly.

Thank you for contributing! 🎉

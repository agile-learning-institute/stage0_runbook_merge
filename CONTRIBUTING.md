# Contributing to Stage0 Runbook Merge

This guide is for developers who want to contribute to the merge utility itself.

## Development Setup

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Python](https://www.python.org/downloads/) 3.12+
- [Pipenv](https://pipenv.pypa.io/en/latest/installation.html)

### Initial Setup
```bash
# Clone the repository
git clone <repository-url>
cd stage0_runbook_merge

# Install dependencies
pipenv install
```

## Testing

The unit testing relies on test data found in the `./test/` folder. The `test/repo/` folder contains the test `process.yaml` file along with simple templates. For testing, these files are copied to `~/tmp/testRepo/` where they can be processed. Files in `test/repo/.stage0_template/test_expected/` are the expected output after merge processing.

## Development Workflow

```bash
# Install dependencies
pipenv install

# Clear test repository
pipenv run clean

# Set up test environment
pipenv run setup

# Run code locally
pipenv run local

# Run unit tests
pipenv run test

# Build container
pipenv run build

# Run black box tests
pipenv run merge
```

### Available Commands
- `pipenv run test` - Run unit tests
- `pipenv run local` - Run the processor locally with test data
- `pipenv run build` - Build the Docker container
- `pipenv run merge` - Run end-to-end tests using the container
- `pipenv run clean` - Clean up test files
- `pipenv run setup` - Set up test environment

## Code Structure

```
src/
├── main.py          # Main processor logic
├── main_test.py     # Unit tests
└── __init__.py

test/
├── repo/            # Test templates and data
│   ├── .stage0_template/
│   │   ├── process.yaml
│   │   ├── test_data/
│   │   └── test_expected/
│   └── [template files]
```

## Adding New Features

1. **Write unit tests** in `src/main_test.py`
2. **Implement the feature** in `src/main.py`
3. **Update test templates** in `test/repo/` if needed
4. **Run unit tests** with `pipenv run test`
5. **Run end-to-end tests** with `pipenv run merge`
6. **Update documentation** as needed

## Code Style Guidelines

- Follow PEP 8 for Python code
- Write descriptive commit messages
- Include unit tests for new features
- Update documentation for user-facing changes

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with appropriate tests
3. Ensure all tests pass (`pipenv run test` and `pipenv run merge`)
4. Update documentation if needed
5. Submit a pull request with a clear description of changes

## Reporting Issues

When reporting issues, please include:
- Description of the problem
- Steps to reproduce
- Expected vs. actual behavior
- Environment details (OS, Python version, etc.)
- Any relevant error messages or logs 
# Stage0 Runbook Merge

A utility for processing code templates by merging them with data from specification YAML files. This tool is designed to be integrated into larger orchestration frameworks and uses the Python [Jinja2 templating library](https://jinja.palletsprojects.com/en/stable/).

## Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Python](https://www.python.org/downloads/) 3.12+
- [Pipenv](https://pipenv.pypa.io/en/latest/installation.html)

### Basic Usage
```bash
# Install dependencies
pipenv install

# Run unit tests
pipenv run test

# Build and test the merge process
pipenv run merge
```

## Documentation

- **[Template Creation Guide](TEMPLATE_GUIDE.md)** - Complete guide for creating templates
- **[Contributing Guide](CONTRIBUTING.md)** - Guide for developers contributing to the utility

## Overview

Stage0 is a software platform that uses AI and Human Centered Design techniques to collect technology-agnostic, parsable design specifications. It then combines those technology-agnostic design files with technology-specific templates to generate functional prototypes in minutes.

This merge utility processes code templates by merging them with data from specification YAML files. The tool is agnostic about folder structure and will process any valid YAML files with a `.yaml` extension.

## Core Concepts

### Specifications
Specifications are loaded from a folder mounted to the container at `/specifications`. The tool processes any valid YAML files with a `.yaml` extension, treating folders as objects containing file-name attributes.

### Templates
Templates and the `.stage0_template/process.yaml` file that drives processing are mounted to the container at `/repo`. This is typically the root of your repository after creating a new repo from a template.

### Process Configuration
The `.stage0_template` folder contains template-specific information:
- `process.yaml` - Configuration file that drives template processing
- `README.md` - Information about how to use the template
- `test_data/` - Test data for validation
- `test_expected/` - Expected output files for testing

## Quick Examples

### Simple Template Processing
```yaml
# process.yaml
templates:
  - path: "./simple.md"
    merge: true
```

### Multiple File Generation
```yaml
# process.yaml
templates:
  - path: "./source.ts"
    mergeFor: 
      items: service.data.sources
      output: "./{{ name }}Service.ts"
```

### Available Filters
```jinja2
{{ data | to_yaml }}           # YAML formatting
{{ data | to_json }}           # Pretty JSON
{{ data | to_json_minified }}  # Compact JSON
{% filter indent(2) %}         # Indentation
{{ content }}
{% endfilter %}
```

## Production Usage

For production deployment, use the Docker container directly:

```bash
docker run --rm \
  -v ~/my-repository:/repo \
  -v ~/my-design:/specifications \
  -e SERVICE_NAME=user \
  -e DATA_SOURCE=organization \
  ghcr.io/agile-learning-institute/stage0_runbook_merge:latest
```

### Mount Points
- Mount the repository to `/repo`
- Mount the design specifications to `/specifications`

### Environment Variables
Use the `-e` option to specify environment variables required by your templates.

## Getting Help

- **Creating templates?** See the [Template Creation Guide](TEMPLATE_GUIDE.md)
- **Contributing code?** See the [Contributing Guide](CONTRIBUTING.md)
- **Found a bug?** [Open an issue](https://github.com/agile-learning-institute/stage0_runbook_merge/issues)
- **Need examples?** Check the `test/repo/` directory for working examples


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

## Table of Contents
- [Overview](#overview)
- [For Template Builders](#for-template-builders)
  - [Core Concepts](#core-concepts)
  - [Processing Workflow](#processing-workflow)
  - [Available Jinja2 Filters](#available-jinja2-filters)
  - [Template Examples](#template-examples)
- [For Contributors](#for-contributors)
  - [Development Setup](#development-setup)
  - [Testing](#testing)
  - [Development Workflow](#development-workflow)
- [Production Usage](#production-usage)

## Overview

Stage0 is a software platform that uses AI and Human Centered Design techniques to collect technology-agnostic, parsable design specifications. It then combines those technology-agnostic design files with technology-specific templates to generate functional prototypes in minutes.

This merge utility processes code templates by merging them with data from specification YAML files. The tool is agnostic about folder structure and will process any valid YAML files with a `.yaml` extension.

---

## For Template Builders

This section is for users who want to create new templates using the existing merge utility.

### Core Concepts

#### Specifications
Specifications are loaded from a folder mounted to the container at `/specifications`. The tool processes any valid YAML files with a `.yaml` extension, treating folders as objects containing file-name attributes.

#### Templates
Templates and the `.stage0_template/process.yaml` file that drives processing are mounted to the container at `/repo`. This is typically the root of your repository after creating a new repo from a template.

#### Process Configuration
The `.stage0_template` folder contains template-specific information:
- `process.yaml` - Configuration file that drives template processing
- `README.md` - Information about how to use the template
- `test_data/` - Test data for validation
- `test_expected/` - Expected output files for testing

### Processing Workflow

The processing follows these steps:
1. Load specifications from YAML files
2. Load environment variables
3. Set context properties
4. Verify required properties exist
5. Merge templates with data
6. Remove the process.yaml file

#### Loading Specifications

Specifications are loaded into a single object available in templates as `{{ specifications }}`. Folders are treated as objects containing file-name attributes, with the `.yaml` extension removed from property names.

**Example folder structure:**
```
/specifications/
├── architecture.yaml
├── dataDictionary.yaml
├── enumerators.yaml
├── personas.yaml
├── dataDefinitions/    
│   ├── dd.user.yaml
│   ├── dd.work-order.yaml
```

This results in a specifications object where `specifications.dataDefinitions.dd.user.description` comes from the `description` property of the `dd.user.yaml` file.

#### Loading Environment Variables

Template repositories often need contextual data for merging. This is accomplished by setting environment variables before processing. The `process.yaml` file lists required environment variables and their expected values.

#### Setting Context Properties

With specifications loaded, you can establish context values that "point" to specific sections of the specifications. There are two ways to set context values:

##### Path Context
Use a reference to a specific property for creating shorthand names:

```yaml
- key: product
  type: path
  path: specifications.architecture.meta.product
```

This allows using `{{ product }}` instead of `{{ specifications.architecture.meta.product }}`.

You can also use template substitution with environment variables:

```yaml
- key: data-source
  type: path
  path: specifications.dataDictionary.primary_document_types.{{ DATA_SOURCE }}
```

##### Filter Context
Select an object from a list by matching a specific value:

```yaml
- key: service
  type: selector
  path: architecture.domains
  filter:
    property: name
    value: "{{ SERVICE_NAME }}"
```

This searches for an object in the `architecture.domains` array where the `name` property matches the `SERVICE_NAME` environment variable.

##### Handling Hyphens in Property Names

Jinja2 templates don't support hyphens in property names as they're interpreted as mathematical operations. Use context to rename properties:

```yaml
- key: productName
  type: path
  path: specifications.architecture.product-name
```

This effectively renames `product-name` to `productName`.

#### Verifying Required Properties

All properties listed under `requires` in the `process.yaml` file are checked to ensure they exist. This allows template authors to place quality constraints around expected data.

#### Merging Templates

Templates are merged with data in several ways:

##### Simple Single-Template Merge
For files that need to be processed and saved with output, use `merge: true`:

```yaml
templates:
  - path: "./simple.md"
    merge: true
```

##### Generating Multiple Output Files (mergeFor)
Create multiple files from the same template based on a list:

```yaml
- path: "./source.ts"
  mergeFor: 
    items: service.data.sources
    output: "./{{ name }}Service.ts"
```

This requires that `items` be an iterable list or dictionary. The current processing item is exposed as `{{ item }}`.

##### Dictionary Iteration in mergeFor
When `items` resolves to a dictionary, the processor iterates over key-value pairs:
- Each iteration provides an `item` with `name` (key) and `content` (value)
- Useful for generating files from folder-mapped dictionaries

```yaml
- path: "./input/dictionary/types/type.yaml.template"
  mergeFor:
    items: specifications.dictionaries.types
    output: "./input/dictionary/types/{{ item.name }}.yaml"
```

##### Generating Multiple Output Files from a Dictionary (mergeFrom)

The `mergeFrom` directive generates multiple files from a dictionary:

```yaml
- path: "./input/dictionary/types/type.yaml.template"
  mergeFrom:
    items: specifications.dictionaries.types
    output: "./input/dictionary/types/{{ item.name }}.yaml"
```

In templates, you can access:
- `{{ item.name }}` - the filename (without .yaml extension)
- `{{ item.content }}` - the full content of the YAML file

**Note:** Use `mergeFrom` for dictionaries and `mergeFor` for lists.

### Available Jinja2 Filters

The template processor provides several custom Jinja2 filters to help format data:

#### `to_yaml` Filter
Converts Python objects to YAML format with proper indentation:
```jinja2
{{ data | to_yaml }}
```

**Example:**
```python
# Input data
{"name": "user", "properties": {"id": "string", "email": "string"}}

# Output
name: user
properties:
  id: string
  email: string
```

#### `to_json` Filter
Converts Python objects to pretty-printed JSON format with indentation and sorted keys:
```jinja2
{{ data | to_json }}
```

**Example:**
```python
# Input data
{"name": "user", "properties": {"id": "string", "email": "string"}}

# Output
{
  "name": "user",
  "properties": {
    "id": "string",
    "email": "string"
  }
}
```

#### `to_json_minified` Filter
Converts Python objects to compact JSON format without spaces:
```jinja2
{{ data | to_json_minified }}
```

**Example:**
```python
# Input data
{"name": "user", "properties": {"id": "string", "email": "string"}}

# Output
{"name":"user","properties":{"id":"string","email":"string"}}
```

#### `indent` Filter
Adds indentation to multi-line strings:
```jinja2
{% filter indent(2) %}
{{ content }}
{% endfilter %}
```

**Example:**
```jinja2
Content: |
{% filter indent(2) %}
line1
line2
{% endfilter %}

# Output
Content: |
  line1
  line2
```

#### Combining Filters
You can combine filters for more complex formatting:
```jinja2
{% filter indent(2) %}
{{ data | to_json }}
{% endfilter %}
```

This produces indented JSON output suitable for embedding in other documents.

### Template Examples

#### Basic Template Structure
```
my-template/
├── .stage0_template/
│   ├── process.yaml
│   ├── test_data/
│   └── test_expected/
├── template1.md
├── template2.ts
└── README.md
```

#### Example process.yaml
```yaml
$schema: "https://stage0/schemas/process.schema.yaml"
$id: "https://stage0/my-template/process.yaml"
title: My Template Process
version: "1.0"

environment:
  SERVICE_NAME: specifies a service name for context
  DATA_SOURCE: document schema file-name for context

context:
  - key: architecture
    type: path
    path: specifications.architecture
  - key: service
    type: selector
    path: architecture.domains
    filter:
      property: name
      value: "{{ SERVICE_NAME }}"

requires:
  - architecture.product
  - service.data.sources

templates:
  - path: "./template1.md"
    merge: true
  - path: "./template2.ts"
    mergeFor: 
      items: service.data.sources
      output: "./{{ name }}Service.ts"
```

---

## For Contributors

This section is for developers who want to contribute to the merge utility itself.

### Development Setup

#### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Python](https://www.python.org/downloads/) 3.12+
- [Pipenv](https://pipenv.pypa.io/en/latest/installation.html)

#### Initial Setup
```bash
# Clone the repository
git clone <repository-url>
cd stage0_runbook_merge

# Install dependencies
pipenv install
```

### Testing

The unit testing relies on test data found in the `./test/` folder. The `test/repo/` folder contains the test `process.yaml` file along with simple templates. For testing, these files are copied to `~/tmp/testRepo/` where they can be processed. Files in `test/repo/.stage0_template/test_expected/` are the expected output after merge processing.

### Development Workflow

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

#### Available Commands
- `pipenv run test` - Run unit tests
- `pipenv run local` - Run the processor locally with test data
- `pipenv run build` - Build the Docker container
- `pipenv run merge` - Run end-to-end tests using the container
- `pipenv run clean` - Clean up test files
- `pipenv run setup` - Set up test environment

#### Code Structure
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

#### Adding New Features
1. Write unit tests in `src/main_test.py`
2. Implement the feature in `src/main.py`
3. Update test templates in `test/repo/` if needed
4. Run `pipenv run test` to verify unit tests pass
5. Run `pipenv run merge` to verify end-to-end tests pass
6. Update documentation as needed

---

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


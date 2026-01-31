# Template Creation Guide

This guide is for users who want to create new templates using the existing merge utility.

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

## Processing Workflow

The processing follows these steps:
1. Load specifications from YAML files
2. Load environment variables
3. Set context properties
4. Verify required properties exist
5. Merge templates with data
6. Remove the process.yaml file

### Loading Specifications

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

### Loading Environment Variables

Template repositories often need contextual data for merging. This is accomplished by setting environment variables before processing. The `process.yaml` file lists required environment variables and their expected values.

### Setting Context Properties

With specifications loaded, you can establish context values that "point" to specific sections of the specifications. There are two ways to set context values:

#### Path Context
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

#### Filter Context
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

#### Handling Hyphens in Property Names

Jinja2 templates don't support hyphens in property names as they're interpreted as mathematical operations. Use context to rename properties:

```yaml
- key: productName
  type: path
  path: specifications.architecture.product-name
```

This effectively renames `product-name` to `productName`.

### Verifying Required Properties

All properties listed under `requires` in the `process.yaml` file are checked to ensure they exist. This allows template authors to place quality constraints around expected data.

### Merging Templates

Templates are merged with data in several ways:

#### Simple Single-Template Merge
For files that need to be processed and saved, use `merge: true`:

```yaml
templates:
  - path: "./simple.md"
    merge: true
```

By default, the template is overwritten in-place. To write to a different file and remove the template, add an optional `output` property (supports Jinja2 for context and environment variables):

```yaml
templates:
  - path: "./README.md.template"
    merge: true
    output: "./README.md"
```

#### Generating Multiple Output Files (mergeFor)
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

#### Generating Multiple Output Files from a Dictionary (mergeFrom)

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

## Available Jinja2 Filters

The template processor provides several custom Jinja2 filters to help format data:

### `to_yaml` Filter
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

### `to_json` Filter
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

### `to_json_minified` Filter
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

### `indent` Filter
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

### Combining Filters
You can combine filters for more complex formatting:
```jinja2
{% filter indent(2) %}
{{ data | to_json }}
{% endfilter %}
```

This produces indented JSON output suitable for embedding in other documents.

## Template Examples

### Basic Template Structure
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

### Example process.yaml
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

## Best Practices

### Template Organization
- Keep templates focused on a single purpose
- Use descriptive file names
- Organize related templates in subdirectories
- Include comprehensive test data

### Error Handling
- Use the `requires` section to validate input data
- Provide clear error messages in templates
- Test with various data scenarios

### Performance
- Avoid complex nested loops in templates
- Use context properties to simplify template logic
- Keep template files reasonably sized

### Documentation
- Include a README.md in your template
- Document required environment variables
- Provide examples of expected output
- Include troubleshooting tips

## Troubleshooting

### Common Issues

**Template not processing:**
- Check that the template path is correct in `process.yaml`
- Verify that required properties exist in specifications
- Ensure environment variables are set correctly

**Incorrect output:**
- Validate your specifications data structure
- Check context property paths
- Review template syntax for errors

**Missing files:**
- Verify that `mergeFor` or `mergeFrom` items exist
- Check output file path templates
- Ensure template files exist in the repository

### Debugging Tips
- Use the `to_yaml` filter to inspect data in templates
- Add debug output to templates temporarily
- Check the processing logs for error messages
- Validate your `process.yaml` syntax 
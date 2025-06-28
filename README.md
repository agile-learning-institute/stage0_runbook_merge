# stageZero_runbook_merge

# Stage Zero overview
Stage0 is a software platform that uses AI and Human Centered Design techniques to collect technology agnostic, parsable design specifications. It then combines those technology agnostic design files with technology specific templates to generate a functional prototype in minutes. 

# Merge Runbook
This utility is used to process code templates, merging them with data from specification yaml files. The utility is meant to be integrated into larger orchestration frameworks. The tool uses the Python [jinja templating library](https://jinja.palletsprojects.com/en/stable/) - this is a [great tutorial](https://ttl255.com/jinja2-tutorial-part-1-introduction-and-variable-substitution/) that will have you up to speed on the important parts quickly. 

## Developer Commands
```bash
# Install dependencies
pipenv install

# Run unit testing
pipenv run test

# Run local code for test/repo
pipenv run local

# Build and use the container to merge test/repo
pipenv run merge

# Just Build the Container
pipenv run build

```

# Table of Contents
- [.stage0_template](#stage0_template) is the folder that identifies this as a template repo
- [process.yaml](#processyaml) file that drives template processing
- [Processing Overview](#processing-overview)
  - [Load Specifications](#loading-specifications)
  - [Load Environment variables. ](#loading-environment-variables)
  - [Set Context properties](#setting-context-properties)
  - [Verify required properties exist]()
  - [Merge the Templates](#merge-templates)
- [Contributing](#contributing)

The data used during template processing is loaded from a folder that is mounted to the container at /specifications. The tool itself is agnostic about the folder structure and files in your specifications folder, it will process any valid yaml files with a .yaml extension. 

The templates, and the ``.stage0_template/process.yaml`` file that drives processing are mounted to the container at /repo. This will likely be the root of your repository after creating a new repo from a template. 

### .stage0_template
This is the folder that contains template specific information. This is where the process.yaml file resides, as well as the template README.md with information about how to use the template. All templates should also have test_data and test_expected folders with appropriate files. These files work with the [test.sh](./test/repo/.stage0_template/test.sh) script to test the template repo. This script must be run from the repo root (a folder that contains a ``./.stage0_template`` subfolder) and will process the templates with the provided test_data, and compare test_expected with the output generated using ``diff``. 

### process.yaml
The ``process.yaml`` file describes how to configure the merge environment, and how to process the templates in the repo. To use the utility you run the processing container with local folders mounted as volumes for ``/specifications`` and ``/repo``. Processing may also require environment values as specified in the ``process.yaml`` file. The ``/repo`` folder must contain the ``process.yaml`` file and all templates. 

This is a configuration based approach to creating data context for merge processing and then processing a collection of templates. The context will always contain a specifications property (see below for information on loading specifications). Additional context is configured in the process.yaml file. 

```yaml
$schema: "https://stage0/schemas/process.schema.yaml"
$id: "https://stage0/template-ts-mongo-express-api/process.yaml"
title: Process file for a typescript, mongo-backed, express based restful API
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
      value: "{{SERVICE_NAME}}"
  - key: data-source
    type: path
    path: specifications.dataDictionary.primary_document_types.{{DATA_SOURCE}}
  - key: productName
    type: path
    path: specifications.architecture.product-name

requires:
  - productName
  - service.data.sources
  - service.data.sinks
  - data-source.description
  - architecture.product
  - architecture.productDescription
  - architecture.organization
  - architecture.organizationName

templates:
  - path: "./simple.md"
    merge: true
  - path: "./loop-in.ts"
    merge: true
  - path: "./source.ts"
    mergeFor: 
      items: service.data.sources
      output: "./{{name}}Service.ts"

```

## Loading Specifications
Specifications are loaded into a single object that is available for use in your templates at {{specifications}}. Folders are treated as objects containing attributes of file-names. The yaml extension is left off of the property name. For example, a specifications folder structure of
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

Would result in a specifications object, and the value ``specifications.dataDefinitions.dd.user.description`` would come from the description property of the dd.user.yaml file in the in the dataDefinitions folder found at the specifications mount point.

# Processing
Once these configurations are loaded the following steps are followed:
- [Load Environment variables. ](#loading-environment-variables)
- [Set Context properties](#setting-context-properties)
  - [Path Context](#setting-a-simple-path-context)
  - [Filter Context](#setting-a-filter-context)
- [Verify required properties exist]()
- [Merge the Templates](#merge-templates)
  - [Single File Merge](#simple-single-template-merge)
  - [Generating Multiple Output files](#generating-multiple-output-files)

After processing is complete, the process.yaml file is removed. 

## Loading Environment Variables
When you setup a template repo, you will undoubtedly need some contextual data to perform the merge, this is accomplished by setting an environment variable before processing. The process.yaml file in the template repo will list the required environment variables and what their values should be. 

## Setting Context properties
With all of the specifications loaded into context, you will sometimes want to identify specific pieces of data that the templates will expect. This can be done by establishing a context value that "points" to the section of the specifications they should process. There are two ways to set a context value
- With a reference to a specific property
- By selecting from a list of objects looking for a match on a specific value. 

### Setting a simple path context
Frequently you will work with a data structure deep in the system, but you would like a "short-hand" name for that value. You Can accomplish this using a path type context.
```yaml
  - key: product
    type: path
    path: specifications.architecture.meta.product
```
Setting this context value allows you to use the simple {{product}} replacement parameter in place of the much longer {{specifications.architecture.meta.product}} key. You can also use template substitution of environment, variables in the path name.
```yaml
  - key: data-source
    type: path
    path: specifications.dataDictionary.primary_document_types.{{DATA_SOURCE}}
```
Setting this context uses the environment variable data_source to establish a context that will be used by your templates. 

### Setting a filter context
If you need to set a context value that's based on looking up on object within a list than the filter context is what you want to use. 
```yaml
  - key: service
    type: selector
    path: architecture.domains
    filter:
      property: name
      value: "{{SERVICE_NAME}}"
```
This filter context looks for an array of objects at the path, and then searches for the object where the property name has the value specified by the environment, variable service name. 

### A note on replacement keys with -
Jinja Templates do not support a ``-`` in property names. The templating engine will Will interpret them as a mathematical operation. In general, it's a good idea to avoid using-in your property names, but sometimes you don't have control over the structure of the documents that you'll be working with. In this case, you can use a context to rename a property.
```
  - key: productName
    type: path
    path: specifications.architecture.product-name
```
This context effectively renames the ``product–name`` property to ``productName``

## Verify Required Properties
All of the properties listed in the processing.yaml file under ``requires`` are checked to make sure they exist. This allows the author of the template to place some quality constraints around the data they expect to be in the specifications.

## Merge Templates
Now that all of the data is set up, it's time to merge templates. The templates identified are merged with data in two ways.

### Simple single-template merge
For files that just need to be processed and saved with the output. We have the simple ``merge: true`` command. This will Cause the template listed to be merged in the rendered document will replace the template file. 
```yaml
templates:
  - path: "./simple.md"
    merge: true
```

### Generating Multiple Output files
There may be instances where you want to create multiple files from the same template file typically based on a list of some sort in the data. This is where the merge for operator comes into play.
```yaml
  - path: "./source.ts"
    mergeFor: 
      items: service.data.sources
      output: "./{{name}}Service.ts"
```
This directive requires that the ``items:`` specified be an iterable List or Dictionary. The template will be merged, and an output file will be generated for each member of the list. The current processing item is exposed in context at the entry ``item``. Values from item are also used to process the output file name, so in the example above each object in the sources List has a name property which is used to create a unique file name for each output file. 

#### Dictionary Iteration in mergeFor
When the `items` path resolves to a dictionary (such as a folder of YAML files), the processor will iterate over its key-value pairs:
- Each iteration provides an `item` with `name` (the key) and `content` (the value)
- This allows you to generate a file for each entry in a folder-mapped dictionary, such as custom types

```yaml
  - path: "./input/dictionary/types/type.yaml.template"
    mergeFor:
      items: specifications.dictionaries.types
      output: "./input/dictionary/types/{{item.name}}.yaml"
```

In the template, you can access:
- `{{item.name}}` - the filename (without .yaml extension)
- `{{item.content}}` - the full content of the YAML file

### Generating Multiple Output files from a Dictionary (mergeFrom)

The `mergeFrom` directive allows you to generate multiple files from a dictionary, such as a folder of YAML files loaded as a dictionary. Each iteration provides an `item` with `name` (the key) and `content` (the value).

Example:
```yaml
  - path: "./input/dictionary/types/type.yaml.template"
    mergeFrom:
      items: specifications.dictionaries.types
      output: "./input/dictionary/types/{{item.name}}.yaml"
```
In the template, you can access:
- `{{item.name}}` - the filename (without .yaml extension)
- `{{item.content}}` - the full content of the YAML file

This is different from `mergeFor`, which is used for iterating over lists. Use `mergeFrom` when your data is a dictionary and you want to generate a file for each key-value pair.

# Contributing

## Prerequisites

Ensure the following tools are installed:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Python](https://www.python.org/downloads/)
- [Pipenv](https://pipenv.pypa.io/en/latest/installation.html)

## Testing
There is not a lot of code, and the unit testing relies on the test data found in the [./test](./test/) folder. The [test/repo](./test/repo/) folder has the test process.yaml file along with a few simple templates. For testing, these files are copied to [test/repo_temp](./test/repo_temp/) where they can be processed. The files in [test/repo_expected](./test/repo_expected/) are what is expected after the merge processing is complete. 

### Install Dependencies
```bash
pipenv install
```

### Clear out the [~/tmp/testRepo](~/tmp.testRepo) folder
```bash
pipenv run clean
```

### Copy [test/repo](./test/repo/) to [~/tmp/testRepo](~/tmp.testRepo)
```bash
pipenv run setup
```
Note: This does clean, then copy

### Run code locally.
```bash
pipenv run local
```
Note: This does clean, copy, then runs the code locally

### Compare output with expected
```bash
pipenv run test
```
Note: This is a ``df`` and will only report errors, no output is good output

### Build the container
```bash
pipenv run build
```

### Run the container
```bash
pipenv run container
```
Note: Will use the utility [test.sh](./.stage0_template/test.sh) script.


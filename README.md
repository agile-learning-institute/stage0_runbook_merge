# stageZero-repo-processor

# POC Context
Stage0 is a software platform that uses AI and Human Centered Design techniques to collect technology agnostic, parsable design specifications. It then combines those technology agnostic design files with technology specific templates to generate 80% of an MVP in minutes instead of months. 

This utility is a proof of concept for the code generation part of the product. We will be building a containerized utility that runs batch style, exiting after processing is complete. 

Key design points
- Uses the data found in SPECIFICATIONS_FOLDER or /specifications
- Processes templates found in REPO_FOLDER or /repo
- Uses a process.yaml configuration file found in /repo to direct processing

## process.yaml
The process.yaml file describes how to configure the merge environment, and how to process the templates in the repo. To use the utility you run the container with local folders mounted as volumes for /specifications and /repo. Processing may also require environment values as specified in the process.yaml file. The /repo folder will contain the process.yaml file and all templates. 

This is a configuration based approach to creating data context for merge processing and then processing a collection of templates. The context will always contain a specifications property (see below for information on loading specifications). Additional context is configured in the process.yaml file. Note that some templates are processed "in-place" meaning that after the merge the template is overwritten with the processed version. Other templates are used to create multiple output files based on some list in the context before being removed. This tool is designed to be a once-and-done utility - TEMPLATE PROCESSING IS DESTRUCTIVE !

sample process.yaml
```
$schema: "https://stage0/schemas/process.schema.yaml"
$id: "https://stage0/template-ts-mongo-express-api/process.yaml"
title: Process file for a typescript, mongo-backed, express based restful API
version: "1.0"

environment:
  - SERVICE_NAME: specifies a service name for context
  - DOCUMENT_SCHEMA: document schema file-name for context

context:
  - service: specifications.architecture.domains[{name: SERVICE_NAME}]
  - document: specifications.dataDefinitions[DOCUMENT_SCHEMA]
  - architecture: specifications.architecture

requires:
  - service.data.sources
  - service.data.sinks
  - document.properties
  - architecture.domain
  - architecture.product
  - architecture.product-name
  - architecture.product-description
  - architecture.organization
  - architecture.organization-name
  - architecture.organization

templates:
  - path: "./simple.md"
    merge: true
  - path: "./loop-in.ts"
    merge: true
  - path: "./source"
    mergeFor: 
      items: service.data.sources
      output: "./{{item.name}}Service.ts"
```

# Processing Overview
We load the process from the process.yaml file and then we load the specifications by reading all yaml files recursively from the  /specifications folder. Then we follow the process.yaml reading data from the environment, setting up context data, validating required data is present, and then processing the templates. 

## Loading Specifications
Specifications are loaded into a single object where folders are treated as objects containing attributes of file-names. The yaml extension is left off of the property name. For example, a specifications folder structure of
```
/specifications/
├── architecture.yaml
├── dataDictionary.yaml
├── enumerators.yaml
├── personas.yaml
├── dataDefinitions/    
│   ├── dd.types/
│   │  ├── word.yaml    
│   │  ├── sentence.yaml
│   │  ├── ...
│   ├── dd.user.yaml
│   ├── dd.work-order.yaml
```

Would result in a context.specifications dictionary and
- The value specifications.architecture.product 
  would come from the product property 
  of the base object in the architecture.yaml file
  found at the specifications mount point
- The value specifications.dataDefinitions.dd.user.description 
  would come from the description property 
  of the dd.user.yaml file in the 
  in the dataDefinitions folder
  found at the specifications mount point


# Future Enhancements
These are anticipated enhancements, issues to come

Schema Rendering: Functions that render ddSchema as json-schema or mongo-schema are needed. This should be implemented with reuse in mind as it is likely to support a new schema management tool. 

Implement new schema management tool that leverages the load specifications features, and the render ddSchema as mongo_schema function to process mongo configurations. Revisit versioning logic and config file structure. Enforce migrations on major only, drop/add indexes, drop/add schema validation per version, upsert Versions, upsert Enumerators. LOAD=True will load test data. Safety breaker will only load test data into empty collections.

Add a RELOAD=True to the schema management tool that causes all data to be deleted and test data to be loaded. Implement safety breaker that prevents reload processing if a key collection has more than a specific number of documents. 


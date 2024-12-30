# stageZero-repo-processor
Tool to process a template repo.

          The following data sources are available
          service - architecture.yaml service object based on service name provided at execution
          collections - collection schema objects for all data sources

# merge processing
## Assemble Merge data 
Env vars
    SERVICE=serviceName 
    ARCHITECTURE_URI=http://....architecture.yaml
    MOUNT=/opt/stageZero/process.yaml

fetch architecture.yaml (resolve $refs)
read process.yaml
data.service = architecture.domains[SERVICE]

## Process Templates
for template process.yaml.templates
    mergeTemplate = fetch(template.path)
    if template.merge
        merge mergeTemplate, data
        write mergeTemplate to template.path
    else if template.mergeFor
        for item in template.items
            data.item = item
            merge mergeTemplate, data
            write mergeTemplate to template.output f`{{item}}`
        delete template.path



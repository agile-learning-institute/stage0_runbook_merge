# JSON Rendering Test

## Pretty JSON Output
```json
{
  "description": "A user of {{product}} including employees and customers",
  "schema": "$ref:./dataDefinitions/dd.user.yaml"
}
```

## Minified JSON Output
```json
{"description":"A user of {{product}} including employees and customers","schema":"$ref:./dataDefinitions/dd.user.yaml"}
```

## YAML Comparison
```yaml
description: A user of {{product}} including employees and customers
schema: $ref:./dataDefinitions/dd.user.yaml
``` 
// Typescript template with a loop
{% for source in service.data.sources -%}
    console.log("{{source.name}}, {{source.backingService}}");
{% endfor %}
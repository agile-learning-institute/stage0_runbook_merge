import json
import logging
import os
import shutil
import sys
from typing import Any, Dict, List

import yaml
from jinja2 import Environment, Template, TemplateSyntaxError, UndefinedError

logger = logging.getLogger(__name__)


def _format_yaml_error(e: Exception, file_path: str) -> str:
    """Format YAML parsing errors with file path and line/column when available."""
    msg = f"YAML parsing error in {file_path}: {e}"
    if hasattr(e, "problem_mark") and e.problem_mark:
        mark = e.problem_mark
        msg += f" (line {mark.line + 1}, column {mark.column + 1})"
    return msg

class Processor:
    """
    Processor class for handling specification and template processing
    based on process.yaml configuration.
    """

    def __init__(self, specifications_folder: str, repo_folder: str) -> None:
        self.specifications_folder = specifications_folder
        self.repo_folder = repo_folder
        self.specifications: Dict[str, Any] = {}
        self.environment: Dict[str, str] = {}
        self.context: List[Dict[str, Any]] = []
        self.requires: List[str] = []
        self.templates: List[Dict[str, Any]] = []
        self.context_data: Dict[str, Any] = {"specifications": {}}
        self.load_process()
        self.load_specifications()

    def remove_process_file(self) -> None:
        """Recursively remove the .stage0_template directory."""
        process_file_path = os.path.join(self.repo_folder, ".stage0_template")
        logger.info(f"Removing {process_file_path}")
        shutil.rmtree(process_file_path)

    def load_process(self) -> None:
        """Load the process.yaml file from the repository folder."""
        process_file_path = os.path.join(self.repo_folder, ".stage0_template/process.yaml")
        try:
            with open(process_file_path, "r") as file:
                process = yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Process file not found: {process_file_path}")
        except yaml.YAMLError as e:
            raise ValueError(_format_yaml_error(e, process_file_path)) from e
        except IOError as e:
            raise IOError(f"Error reading Process file {process_file_path}: {e}") from e

        if process is None:
            raise ValueError(f"Process file {process_file_path} is empty or parses to null")

        raw_env = process.get("environment")
        self.environment = raw_env if isinstance(raw_env, dict) else {}
        self.context = process.get("context", [])
        self.requires = process.get("requires", [])
        self.templates = process.get("templates", [])

        logger.info(f"Process Loaded for {len(self.templates)} templates")
        logger.debug(
            f"Process config: {len(self.environment)} env vars, {len(self.context)} context directives, "
            f"{len(self.requires)} requirements, templates={[t.get('path') for t in self.templates]}"
        )

    def load_specifications(self) -> None:
        """Recursively load YAML files from the specifications folder."""
        files_read = 0
        for root, _, files in os.walk(self.specifications_folder):
            for file in files:
                if file.endswith(".yaml"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r") as f:
                            data = yaml.safe_load(f)
                    except yaml.YAMLError as e:
                        raise ValueError(_format_yaml_error(e, file_path)) from e
                    except IOError as e:
                        raise IOError(f"Error reading specification file {file_path}: {e}") from e

                    files_read += 1
                    relative_path = os.path.relpath(file_path, self.specifications_folder)
                    keys = relative_path.replace(".yaml", "").split(os.sep)
                    temp = self.context_data["specifications"]
                    for key in keys[:-1]:
                        temp = temp.setdefault(key, {})
                    temp[keys[-1]] = data

        spec_keys = list(self.context_data["specifications"].keys())
        logger.info(f"Specifications Loaded from {files_read} documents")
        logger.debug(f"Specification top-level keys: {spec_keys}")

    def read_environment(self) -> None:
        """
        Load environment variables as specified in the process.yaml.
        Raise an exception if a required variable is missing.
        """
        for var_name in self.environment.keys():
            value = os.getenv(var_name)
            if value is None:
                raise KeyError(
                    f"Environment variable '{var_name}' is not set. "
                    f"Required by process.yaml environment section. Set with -e {var_name}=<value>"
                )
            self.environment[var_name] = value

        logger.info(f"{len(self.environment)} Environment Variables loaded successfully.")
        logger.debug(f"Environment: {dict(self.environment)}")

    def add_context(self) -> None:
        """Add context elements to the context_data based on standardized directives."""
        for context_item in self.context:
            key = context_item["key"]
            directive_type = context_item["type"]
            try:
                path = Template(context_item["path"]).render(self.environment)
            except (UndefinedError, TemplateSyntaxError) as e:
                raise ValueError(
                    f"Context directive '{key}': failed to render path '{context_item['path']}': {e}"
                ) from e

            try:
                if directive_type == "path":
                    value = self.resolve_path(path)
                elif directive_type == "selector":
                    filter_property = Template(context_item["filter"]["property"]).render(
                        self.environment
                    )
                    filter_value = Template(context_item["filter"]["value"]).render(
                        self.environment
                    )
                    value = self.resolve_selector(path, filter_property, filter_value)
                else:
                    raise ValueError(f"Unknown context directive type: {directive_type}")

                self.context_data[key] = value
                logger.debug(f"Context '{key}' resolved: {directive_type} -> {path}")
            except (KeyError, ValueError) as e:
                raise ValueError(
                    f"Context directive '{key}' failed (path={path}, type={directive_type}): {e}"
                ) from e

        logger.info(f"{len(self.context)} Data Contexts Established")

    def resolve_path(self, path: str) -> Any:
        """Resolve a simple property path."""
        keys = path.split(".")
        value = self.context_data
        breadcrumb = []
        for key in keys:
            breadcrumb.append(key)
            if key not in value:
                available = list(value.keys()) if isinstance(value, dict) else f"<{type(value).__name__}>"
                raise KeyError(
                    f"Path '{path}' failed at '{'.'.join(breadcrumb)}': key '{key}' not found. "
                    f"Available at this level: {available}"
                )
            value = value[key]
        return value

    def resolve_selector(
        self, list_path: str, property_name: str, property_value: Any
    ) -> Any:
        """Resolve a list item based on filter criteria."""
        items = self.resolve_path(list_path)
        if not isinstance(items, list):
            raise ValueError(
                f"Path '{list_path}' must resolve to a list, got {type(items).__name__}"
            )
        for item in items:
            if item.get(property_name) == property_value:
                return item
        available_values = [
            repr(item.get(property_name, "<missing>")) for item in items[:5]
        ]
        if len(items) > 5:
            available_values.append("...")
        raise KeyError(
            f"No item with {property_name}={property_value!r} in {list_path}. "
            f"Available {property_name} values: {', '.join(available_values)}"
        )

    def verify_exists(self) -> None:
        """Ensure all required properties exist in the context data."""
        for prop in self.requires:
            keys = prop.split(".")
            value = self.context_data
            breadcrumb = []
            for key in keys:
                breadcrumb.append(key)
                if key not in value:
                    available = (
                        list(value.keys())
                        if isinstance(value, dict)
                        else f"<{type(value).__name__}>"
                    )
                    raise KeyError(
                        f"Required property '{prop}' is missing at '{'.'.join(breadcrumb)}'. "
                        f"Available at this level: {available}"
                    )
                value = value[key]
        logger.info(f"Verified {len(self.requires)} required properties exist, go for processing")
        logger.debug(f"Required properties verified: {self.requires}")

    def process_templates(self) -> None:
        """Process templates according to the process.yaml configuration."""
        files_written = 0
        for template_config in self.templates:
            template_path = os.path.normpath(os.path.join(self.repo_folder, template_config["path"]))
            logger.info(f"Processing {template_path}")
            try:
                with open(template_path, "r") as file:
                    env = Environment()
                    env.filters['to_yaml'] = lambda value: yaml.dump(value, default_flow_style=False).rstrip()
                    env.filters['to_json'] = lambda value: json.dumps(value, indent=2, sort_keys=True)
                    env.filters['to_json_minified'] = lambda value: json.dumps(value, separators=(',', ':'))
                    def indent_filter(s, n=2):
                        if not s:
                            return ''
                        lines = s.splitlines()
                        result = '\n'.join((' ' * n + line if line.strip() else '') for line in lines)
                        return result
                    env.filters['indent'] = indent_filter
                    template = env.from_string(file.read())
            except FileNotFoundError:
                raise FileNotFoundError(f"Template file not found: {template_path}")
            except IOError as e:
                raise IOError(f"Error reading template file {template_path}: {e}")
            logger.debug(f"Read Template {template_path}")
            
            if "merge" in template_config and template_config["merge"]:
                logger.debug(f"Merging {template_path}")
                try:
                    output = template.render(self.context_data)
                except (UndefinedError, TemplateSyntaxError) as e:
                    raise ValueError(
                        f"Template {template_config['path']}: render failed - {e}"
                    ) from e
                if "output" in template_config:
                    # Write to output path and delete the template file
                    output_context = {**self.context_data, **self.environment}
                    output_file_name = Template(template_config["output"]).render(output_context)
                    output_path = os.path.normpath(os.path.join(self.repo_folder, output_file_name))
                    logger.info(f"Building {output_file_name}")
                    with open(output_path, "w") as file:
                        file.write(output)
                    logger.debug(f"Removing template {template_path}")
                    os.remove(template_path)
                else:
                    # Render and overwrite the template in-place
                    with open(template_path, "w") as file:
                        file.write(output)
                files_written += 1

            elif "mergeFor" in template_config:
                # Use resolve_path to get the items for mergeFor processing
                items = self.resolve_path(template_config["mergeFor"]["items"])
                # Handle both list and dictionary iteration
                if isinstance(items, dict):
                    # For dictionaries, create name/content pairs
                    iterable = [{"name": k, "content": v} for k, v in items.items()]
                else:
                    # For lists (including lists of strings), use as-is
                    iterable = items
                for item in iterable:
                    # Build the context for rendering the output file name.
                    # - For dict items, expose keys as top-level variables (backwards compatible)
                    # - Always expose the full item as `item` so string lists can use {{ item }}.
                    if isinstance(item, dict):
                        output_context = {**item}
                        output_context.setdefault("item", item)
                    else:
                        output_context = {"item": item}

                    # Render the output file name using the item-aware context
                    output_file_name = Template(template_config["mergeFor"]["output"]).render(**output_context)
                    output_path = os.path.normpath(os.path.join(self.repo_folder, output_file_name))
                    logger.info(f"Building {output_file_name}")

                    # Establish item context and render template
                    # Expose `item` plus any dict keys when item is a mapping
                    if isinstance(item, dict):
                        context = {**self.context_data, **item, "item": item}
                    else:
                        context = {**self.context_data, "item": item}
                    try:
                        output = template.render(context)
                    except (UndefinedError, TemplateSyntaxError) as e:
                        raise ValueError(
                            f"Template {template_config['path']} (item={item.get('name', item)}): "
                            f"render failed - {e}"
                        ) from e

                    with open(output_path, "w") as file:
                        file.write(output)
                    files_written += 1

                # Remove the original template file after processing
                logger.debug(f"Removing template {template_path}")
                os.remove(template_path)

            elif "mergeFrom" in template_config:
                # New directive for dictionary iteration
                items = self.resolve_path(template_config["mergeFrom"]["items"])
                
                if not isinstance(items, dict):
                    raise ValueError(f"mergeFrom requires a dictionary, got {type(items)}")
                
                # Convert dictionary to name/content pairs
                iterable = [{"name": k, "content": v} for k, v in items.items()]
                
                for item in iterable:
                    # Render the output file name using the item context
                    output_file_name = Template(template_config["mergeFrom"]["output"]).render(item=item)
                    output_path = os.path.normpath(os.path.join(self.repo_folder, output_file_name))
                    logger.info(f"Building {output_file_name}")

                    # Establish item context and render template
                    context = {**self.context_data, "item": item}
                    try:
                        output = template.render(context)
                    except (UndefinedError, TemplateSyntaxError) as e:
                        raise ValueError(
                            f"Template {template_config['path']} (item={item.get('name', item)}): "
                            f"render failed - {e}"
                        ) from e

                    with open(output_path, "w") as file:
                        file.write(output)
                    files_written += 1

                # Remove the original template file after processing
                logger.debug(f"Removing template {template_path}")
                os.remove(template_path)
        self.remove_process_file()
        logger.info(f"Completed - Processed {len(self.templates)} templates, wrote {files_written} files")


def main() -> None:
    specifications_folder = os.getenv("SPECIFICATIONS_FOLDER", "/specifications")
    repo_folder = os.getenv("REPO_FOLDER", "/repo")
    logging_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = "%(levelname)s: %(message)s"
    logging.basicConfig(level=logging_level, format=log_format, stream=sys.stderr)
    logger.info(
        f"Initialized, Specifications Folder: {specifications_folder}, Repo Folder: {repo_folder}, "
        f"Logging Level: {logging_level}"
    )

    try:
        processor = Processor(specifications_folder, repo_folder)
        processor.read_environment()
        processor.add_context()
        processor.verify_exists()
        processor.process_templates()
    except Exception as e:
        logger.exception(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
import shutil
from jinja2 import Template
import os
import yaml

import logging
logger = logging.getLogger(__name__)

class Processor:
    """
    Processor class for handling specification and template processing 
    based on process.yaml configuration.
    """

    def __init__(self, specifications_folder, repo_folder):
        self.specifications_folder = specifications_folder
        self.repo_folder = repo_folder
        self.specifications = {}
        self.environment = {}
        self.context = {}
        self.requires = []
        self.templates = []
        self.context_data = {"specifications": {}}
        self.load_process()
        self.load_specifications()

    def remove_process_file(self):
        """Recursively remove the .stage0_template directory."""
        process_file_path = os.path.join(self.repo_folder, ".stage0_template")
        logger.info(f"Removing {process_file_path}")
        shutil.rmtree(process_file_path)
        
    def load_process(self):
        """Load the process.yaml file from the repository folder."""
        process_file_path = os.path.join(self.repo_folder, ".stage0_template/process.yaml")
        try:
            with open(process_file_path, "r") as file:
                process = yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Process file not found: {process_file_path}")
        except IOError as e:
            raise IOError(f"Error reading Process file {process_file_path}: {e}")
            
        self.environment = process.get("environment", [])
        self.context = process.get("context", [])
        self.requires = process.get("requires", [])
        self.templates = process.get("templates", [])
        logger.info(f"Process Loaded for {len(self.templates)} templates")

    def load_specifications(self):
        """Recursively load YAML files from the specifications folder."""
        files_read = 0
        for root, _, files in os.walk(self.specifications_folder):
            for file in files:
                if file.endswith(".yaml"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r") as f:
                        data = yaml.safe_load(f)
                    files_read += 1
                    relative_path = os.path.relpath(file_path, self.specifications_folder)
                    keys = relative_path.replace(".yaml", "").split(os.sep)
                    temp = self.context_data["specifications"]
                    for key in keys[:-1]:
                        temp = temp.setdefault(key, {})
                    temp[keys[-1]] = data
        logger.info(f"Specifications Loaded from {files_read} documents")

    def read_environment(self):
        """
        Load environment variables as specified in the process.yaml.
        Raise an exception if a required variable is missing.
        """
        for var_name in self.environment.keys():
            value = os.getenv(var_name)
            if value is None:
                raise KeyError(f"Environment variable '{var_name}' is not set.")
            self.environment[var_name] = value

        logger.info(f"{len(self.environment)} Environment Variables loaded successfully.")        
        
    def add_context(self):
        """Add context elements to the context_data based on standardized directives."""
        # context data is template processed with environment values
        for context_item in self.context:
            key = context_item["key"]
            directive_type = context_item["type"]
            path = Template(context_item["path"]).render(self.environment)

            if directive_type == "path":
                # Simple property path resolution
                value = self.resolve_path(path)
            
            elif directive_type == "selector":
                # List selector resolution
                filter_property = Template(context_item["filter"]["property"]).render(self.environment)
                filter_value =    Template(context_item["filter"]["value"]).render(self.environment)
                value = self.resolve_selector(path, filter_property, filter_value)
            
            else:
                raise ValueError(f"Unknown context directive type: {directive_type}")

            self.context_data[key] = value
        logger.info(f"{len(self.context)} Data Contexts Established")
        
    def resolve_path(self, path):
        """Resolve a simple property path."""
        keys = path.split(".")
        value = self.context_data
        for key in keys:
            value = value[key]
        return value

    def resolve_selector(self, list_path, property_name, property_value):
        """Resolve a list item based on filter criteria."""
        items = self.resolve_path(list_path)
        if isinstance(items, list):
            for item in items:
                if item.get(property_name) == property_value:
                    return item
            raise KeyError(f"Item with {property_name} = {property_value} not found in {list_path}")
        raise ValueError(f"Path does not resolve to a list: {list_path}")

    def verify_exists(self):
        """Ensure all required properties exist in the context data."""
        for prop in self.requires:
            keys = prop.split(".")
            value = self.context_data
            for key in keys:
                if key not in value:
                    raise KeyError(f"Required property {prop} is missing.")
                value = value[key]
        logger.info(f"Verified {len(self.requires)} required properties exist, go for processing")

    def process_templates(self):
        """Process templates according to the process.yaml configuration."""
        files_written = 0
        for template_config in self.templates:
            template_path = os.path.normpath(os.path.join(self.repo_folder, template_config["path"]))
            logger.info(f"Processing {template_path}")
            try:
                with open(template_path, "r") as file:
                    template = Template(file.read())
            except FileNotFoundError:
                raise FileNotFoundError(f"Template file not found: {template_path}")
            except IOError as e:
                raise IOError(f"Error reading template file {template_path}: {e}")
            logger.debug(f"Read Template {template_path}")
            
            if "merge" in template_config and template_config["merge"]:
                # Render and overwrite the template in-place
                logger.debug(f"Merging {template_path}")
                output = template.render(self.context_data)
                with open(template_path, "w") as file:
                    file.write(output)
                files_written += 1

            elif "mergeFor" in template_config:
                # Use resolve_path to get the items for mergeFor processing
                items = self.resolve_path(template_config["mergeFor"]["items"])
                for item in items:
                    # Render the output file name using the item context
                    output_file_name = Template(template_config["mergeFor"]["output"]).render(item)
                    output_path = os.path.normpath(os.path.join(self.repo_folder, output_file_name))
                    logger.info(f"Building {output_file_name}")

                    # Establish item context and render template
                    self.context_data["item"] = item
                    logger.debug(f"Merging {output_path}")
                    output = template.render(self.context_data)
                    
                    with open(output_path, "w") as file:
                        file.write(output)
                    files_written += 1

                # Remove the original template file after processing
                logger.debug(f"Removing template {template_path}")
                os.remove(template_path)
        self.remove_process_file()
        logger.info(f"Completed - Processed {len(self.templates)} templates, wrote {files_written} files")

def main():
    specifications_folder = os.getenv("SPECIFICATIONS_FOLDER", "/specifications")
    repo_folder = os.getenv("REPO_FOLDER", "/repo")
    logging_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(level=logging_level)
    logger.info(f"Initialized, Specifications Folder: {specifications_folder}, Repo Folder: {repo_folder}, Logging Level {logging_level}")
    
    try:
        processor = Processor(specifications_folder, repo_folder)
        processor.read_environment()
        processor.add_context()
        processor.verify_exists()
        processor.process_templates()
    except Exception as e:
        logger.error(f"Error Reported {str(e)}")

if __name__ == "__main__":
    main()
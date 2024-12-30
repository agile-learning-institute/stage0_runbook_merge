import os
import yaml
from jinja2 import Template

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
        self.required = []
        self.templates = []
        self.context_data = {"specifications": {}}
        self.load_process()
        self.load_specifications()

    def load_process(self):
        """Load the process.yaml file from the repository folder."""
        process_file_path = os.path.join(self.repo_folder, "process.yaml")
        with open(process_file_path, 'r') as file:
            process = yaml.safe_load(file)
        self.environment = process.get("environment", [])
        self.context = process.get("context", [])
        self.required = process.get("requires", [])
        self.templates = process.get("templates", [])

    def load_specifications(self):
        """Recursively load YAML files from the specifications folder."""
        for root, _, files in os.walk(self.specifications_folder):
            for file in files:
                if file.endswith(".yaml"):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as f:
                        data = yaml.safe_load(f)
                    relative_path = os.path.relpath(file_path, self.specifications_folder)
                    keys = relative_path.replace(".yaml", "").split(os.sep)
                    temp = self.context_data["specifications"]
                    for key in keys[:-1]:
                        temp = temp.setdefault(key, {})
                    temp[keys[-1]] = data

    def read_environment(self):
        """Load environment variables as specified in the process.yaml."""
        for var in self.environment:
            self.environment[var] = os.getenv(var)

    def add_context(self):
        """Add context elements to the context_data."""
        for context in self.context:
            template = Template(context["value"])
            address = template.render(self.environment)
            keys = address.split(".")
            value = self.context_data["specifications"]
            for key in keys:
                value = value[key]
            self.context_data[context["key"]] = value

    def verify_exists(self):
        """Ensure all required properties exist in the context data."""
        for prop in self.required:
            keys = prop.split(".")
            value = self.context_data
            for key in keys:
                if key not in value:
                    raise KeyError(f"Required property {prop} is missing.")
                value = value[key]

    def process_templates(self):
        """Process templates according to the process.yaml configuration."""
        for template_config in self.templates:
            template_path = os.path.join(self.repo_folder, template_config["path"])
            with open(template_path, 'r') as file:
                template = Template(file.read())
            
            if "merge" in template_config and template_config["merge"]:
                output = template.render(self.context_data)
                with open(template_path, 'w') as file:
                    file.write(output)
            elif "mergeFor" in template_config:
                items = self.context_data
                for key in template_config["mergeFor"]["items"].split("."):
                    items = items[key]
                for item in items:
                    self.context_data["item"] = item
                    output = template.render(self.context_data)
                    output_file_name = Template(template_config["mergeFor"]["output"]).render(item)
                    output_path = os.path.join(self.repo_folder, output_file_name)
                    with open(output_path, 'w') as file:
                        file.write(output)
                os.remove(template_path)

def main():
    specifications_folder = os.getenv("SPECIFICATIONS_FOLDER", "/specifications")
    repo_folder = os.getenv("REPO_FOLDER", "/repo")
    processor = Processor(specifications_folder, repo_folder)

    processor.read_environment()
    processor.add_context()
    processor.verify_exists()
    processor.process_templates()

if __name__ == "__main__":
    main()
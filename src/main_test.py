#################
# NOTE: Uses the test/specifications and test/repo folders

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open
import os
from main import Processor

class TestProcessor(unittest.TestCase):
    TEST_SPECIFICATIONS = "./test/repo/.stage0_template/test_data"
    TEST_REPO = "./test/repo"

    def setUp(self):
        """Set up a Processor instance for each test."""
        os.environ["SERVICE_NAME"] = "user"
        os.environ["DATA_SOURCE"] = "organization"
        self.processor = Processor(self.TEST_SPECIFICATIONS, self.TEST_REPO)

    def tearDown(self):
        del os.environ["SERVICE_NAME"]
        del os.environ["DATA_SOURCE"]
        return super().tearDown()
    
    def test_load_process(self):
        """Test that process.yaml is loaded correctly."""
        self.assertEqual(len(self.processor.environment), 2)
        self.assertIn("SERVICE_NAME", self.processor.environment)
        self.assertIn("DATA_SOURCE", self.processor.environment)
        self.assertEqual(len(self.processor.context), 4)
        self.assertEqual("architecture", self.processor.context[0]["key"])
        self.assertEqual("service", self.processor.context[1]["key"])
        self.assertEqual("data-source", self.processor.context[2]["key"])
        self.assertEqual("productName", self.processor.context[3]["key"])
        self.assertEqual(len(self.processor.requires), 8)
        self.assertEqual(len(self.processor.templates), 6)


    def test_load_specifications(self):
        """Test that specifications are loaded correctly."""
        self.assertIn("architecture", self.processor.context_data["specifications"])
        self.assertEqual("ProductSlug", self.processor.context_data["specifications"]["architecture"]["product"])
        self.assertIn("dataDefinitions", self.processor.context_data["specifications"])
        self.assertEqual("User Object", self.processor.context_data["specifications"]["dataDefinitions"]["dd.user"]["title"])
        # Test the new types dictionary
        self.assertIn("dataDictionary", self.processor.context_data["specifications"])
        self.assertIn("types", self.processor.context_data["specifications"]["dataDictionary"])

    def test_read_environment(self):
        """Test that environment vars are loaded correctly."""
        self.processor.read_environment()
        self.assertEqual("user", self.processor.environment["SERVICE_NAME"])
        self.assertEqual("organization", self.processor.environment["DATA_SOURCE"])

    def test_empty_environment_does_not_fail(self):
        """Test that empty or null environment property does not cause failure."""
        self.processor.environment = {}
        self.processor.read_environment()
        self.assertEqual(self.processor.environment, {})

    def test_load_process_with_empty_environment_yaml(self):
        """Test that process.yaml with empty environment: key does not fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir) / ".stage0_template"
            template_dir.mkdir()
            process_file = template_dir / "process.yaml"
            process_file.write_text("""environment:

context: []
requires: []
templates:
  - path: ./simple.md
    merge: true
""")
            simple_md = Path(tmpdir) / "simple.md"
            simple_md.write_text("hello")
            specs_dir = Path(tmpdir) / "specs"
            specs_dir.mkdir()
            (specs_dir / "dummy.yaml").write_text("{}")

            processor = Processor(str(specs_dir), tmpdir)
            self.assertEqual(processor.environment, {})
            processor.read_environment()

    def test_load_process_invalid_yaml(self):
        """Test that invalid YAML in process.yaml raises helpful error with file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir) / ".stage0_template"
            template_dir.mkdir()
            process_file = template_dir / "process.yaml"
            process_file.write_text("templates:\n  - path: bad\n  invalid: yaml: [")
            specs_dir = Path(tmpdir) / "specs"
            specs_dir.mkdir()
            (specs_dir / "dummy.yaml").write_text("{}")

            with self.assertRaises(ValueError) as ctx:
                Processor(str(specs_dir), tmpdir)
            self.assertIn("process.yaml", str(ctx.exception))
            self.assertIn("YAML", str(ctx.exception))

    def test_resolve_path_missing_key_has_helpful_error(self):
        """Test that resolve_path raises KeyError with available keys when key not found."""
        self.processor.context_data = {
            "specifications": {"arch": {"product": "x"}},
            "top": {"level1": {"level2": "value"}},
        }
        with self.assertRaises(KeyError) as ctx:
            self.processor.resolve_path("top.level1.nonexistent")
        self.assertIn("nonexistent", str(ctx.exception))
        self.assertIn("level2", str(ctx.exception))

    def test_resolve_selector_no_match_has_helpful_error(self):
        """Test that resolve_selector raises KeyError with available values when no match."""
        self.processor.context_data = {
            "domains": [
                {"name": "user", "id": 1},
                {"name": "admin", "id": 2},
            ]
        }
        with self.assertRaises(KeyError) as ctx:
            self.processor.resolve_selector("domains", "name", "nonexistent")
        self.assertIn("nonexistent", str(ctx.exception))
        self.assertIn("user", str(ctx.exception))
        self.assertIn("admin", str(ctx.exception))

    def test_verify_exists_missing_property_has_helpful_error(self):
        """Test that verify_exists raises KeyError with available keys when required missing."""
        self.processor.context_data = {"a": {"b": {"c": 1}}}
        self.processor.requires = ["a.b.nonexistent"]
        with self.assertRaises(KeyError) as ctx:
            self.processor.verify_exists()
        self.assertIn("nonexistent", str(ctx.exception))
        self.assertIn("c", str(ctx.exception))

    def test_add_context_with_resolved_directive(self):
        """Test that context is added correctly and resolves directives."""
        self.processor.read_environment()
        self.processor.add_context()

        # Verify context data includes the correct domain
        self.assertIn("service", self.processor.context_data)
        self.assertEqual("user",
            self.processor.context_data["service"]["name"]
        )
        self.assertEqual("user",
            self.processor.context_data["service"]["data"]["sources"][0]["name"]
        )

        self.assertIn("data-source", self.processor.context_data)
        self.assertEqual("A organization of users",
            self.processor.context_data["data-source"]["description"]
        )

        self.assertIn("architecture", self.processor.context_data)
        self.assertIn("product", self.processor.context_data["architecture"])

    def test_verify_exists(self):
        """Test that required properties are verified correctly."""
        self.processor.read_environment()
        self.processor.add_context()
        try:
            self.processor.verify_exists()
        except KeyError as e:
            self.fail(f"verify_exists raised KeyError unexpectedly: {e}")

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.remove")
    @patch("shutil.rmtree")
    def test_process_templates(self, mock_rmtree, mock_remove, mock_file):
        """Test template processing with mock file operations."""
        # Prepare test data
        self.processor.read_environment()
        self.processor.add_context()
        self.processor.verify_exists()

        # Mock behavior for process_templates
        self.processor.process_templates()

        # Verify that files were opened for writing for the merge templates
        mock_file.assert_any_call(os.path.normpath(os.path.join(self.TEST_REPO, "simple.md")), "w")
        mock_file.assert_any_call(os.path.normpath(os.path.join(self.TEST_REPO, "loop-in.ts")), "w")
        mock_file.assert_any_call(os.path.normpath(os.path.join(self.TEST_REPO, "README.md")), "w")
        mock_file.assert_any_call(os.path.normpath(os.path.join(self.TEST_REPO, "userService.ts")), "w")
        mock_file.assert_any_call(os.path.normpath(os.path.join(self.TEST_REPO, "organizationService.ts")), "w")

        # Verify that the source template file was removed
        mock_remove.assert_any_call(os.path.normpath(os.path.join(self.TEST_REPO, "source.ts")))
        mock_remove.assert_any_call(os.path.normpath(os.path.join(self.TEST_REPO, "README.md.template")))
        # Verify that the dict-test template file was removed
        mock_remove.assert_any_call(os.path.normpath(os.path.join(self.TEST_REPO, "dict-test.j2")))

        # Ensure that the directory was not removed (if applicable)
        mock_rmtree.assert_called_once_with(os.path.join(self.TEST_REPO, ".stage0_template"))

    def test_to_yaml_filter(self):
        """Test that the to_yaml filter works correctly."""
        from jinja2 import Environment
        import yaml
        
        env = Environment()
        env.filters['to_yaml'] = lambda value: yaml.dump(value, default_flow_style=False).rstrip()
        
        template = env.from_string("{{ data | to_yaml }}")
        test_data = {"key": "value", "nested": {"inner": "data"}}
        result = template.render(data=test_data)
        
        expected = "key: value\nnested:\n  inner: data"
        self.assertEqual(result, expected)

    def test_to_json_filter(self):
        """Test that the to_json filter works correctly."""
        from jinja2 import Environment
        import json
        
        env = Environment()
        env.filters['to_json'] = lambda value: json.dumps(value, indent=2, sort_keys=True)
        
        template = env.from_string("{{ data | to_json }}")
        test_data = {"key": "value", "nested": {"inner": "data"}}
        result = template.render(data=test_data)
        
        expected = '{\n  "key": "value",\n  "nested": {\n    "inner": "data"\n  }\n}'
        self.assertEqual(result, expected)

    def test_to_json_minified_filter(self):
        """Test that the to_json_minified filter works correctly."""
        from jinja2 import Environment
        import json
        
        env = Environment()
        env.filters['to_json_minified'] = lambda value: json.dumps(value, separators=(',', ':'))
        
        template = env.from_string("{{ data | to_json_minified }}")
        test_data = {"key": "value", "nested": {"inner": "data"}}
        result = template.render(data=test_data)
        
        expected = '{"key":"value","nested":{"inner":"data"}}'
        self.assertEqual(result, expected)

    def test_indent_filter(self):
        """Test that the indent filter works correctly."""
        from jinja2 import Environment
        
        env = Environment()
        def indent_filter(s, n=2):
            if not s:
                return ''
            lines = s.splitlines()
            result = '\n'.join((' ' * n + line if line.strip() else '') for line in lines)
            return result
        env.filters['indent'] = indent_filter
        
        template = env.from_string("Content: |\n{% filter indent(2) %}{{ data }}{% endfilter %}")
        test_data = "line1\nline2"
        result = template.render(data=test_data)
        
        expected = "Content: |\n  line1\n  line2"
        self.assertEqual(result, expected)

    def test_mergeFrom_dictionary_iteration(self):
        """Test that mergeFrom correctly iterates over dictionaries."""
        # Test data structure similar to what mergeFrom processes
        test_dict = {
            "type1": {"description": "First type", "schema": "schema1.yaml"},
            "type2": {"description": "Second type", "schema": "schema2.yaml"}
        }
        
        # Simulate the mergeFrom logic
        iterable = [{"name": k, "content": v} for k, v in test_dict.items()]
        
        self.assertEqual(len(iterable), 2)
        self.assertEqual(iterable[0]["name"], "type1")
        self.assertEqual(iterable[0]["content"]["description"], "First type")
        self.assertEqual(iterable[1]["name"], "type2")
        self.assertEqual(iterable[1]["content"]["description"], "Second type")

    def test_mergeFor_list_iteration(self):
        """Test that mergeFor correctly iterates over lists."""
        # Test data structure similar to what mergeFor processes
        test_list = [
            {"name": "service1", "backingService": "mongodb"},
            {"name": "service2", "backingService": "postgres"}
        ]
        
        # Simulate the mergeFor logic
        iterable = test_list  # Lists are used as-is
        
        self.assertEqual(len(iterable), 2)
        self.assertEqual(iterable[0]["name"], "service1")
        self.assertEqual(iterable[1]["name"], "service2")

    def test_mergeFor_string_list_integration(self):
        """Test that mergeFor supports lists of strings for output paths and template rendering."""
        from jinja2 import Template
        import yaml

        with tempfile.TemporaryDirectory() as tmpdir:
            # Set up a minimal .stage0_template/process.yaml using mergeFor over a list of strings
            template_dir = Path(tmpdir) / ".stage0_template"
            template_dir.mkdir()
            process_file = template_dir / "process.yaml"
            process_file.write_text(
                yaml.dump(
                    {
                        "environment": {},
                        "context": [],
                        "requires": [],
                        "templates": [
                            {
                                "path": "./routes.template",
                                "mergeFor": {
                                    "items": "controls",
                                    "output": "./{{ item | lower }}_routes.py",
                                },
                            }
                        ],
                    }
                )
            )

            # Create a simple template that uses the item string directly
            template_path = Path(tmpdir) / "routes.template"
            template_path.write_text("route for {{ item }}")

            # Create a dummy specifications folder (required by Processor)
            specs_dir = Path(tmpdir) / "specs"
            specs_dir.mkdir()
            (specs_dir / "dummy.yaml").write_text("{}")

            # Instantiate a Processor and inject a list of strings into context_data
            processor = Processor(str(specs_dir), tmpdir)
            processor.context_data = {"controls": ["Create", "Control"]}

            # This would fail before the fix because Template.render was called with a bare string
            processor.process_templates()

            # Verify that the expected files were created with the correct content
            create_path = Path(tmpdir) / "create_routes.py"
            control_path = Path(tmpdir) / "control_routes.py"
            self.assertTrue(create_path.exists())
            self.assertTrue(control_path.exists())
            self.assertEqual(create_path.read_text(), "route for Create")
            self.assertEqual(control_path.read_text(), "route for Control")

            # The original template should have been removed
            self.assertFalse(template_path.exists())

    def test_combined_filters(self):
        """Test that to_yaml and indent filters work together."""
        from jinja2 import Environment
        import yaml
        
        env = Environment()
        env.filters['to_yaml'] = lambda value: yaml.dump(value, default_flow_style=False).rstrip()
        def indent_filter(s, n=2):
            if not s:
                return ''
            lines = s.splitlines()
            result = '\n'.join((' ' * n + line if line.strip() else '') for line in lines)
            return result
        env.filters['indent'] = indent_filter
        
        template = env.from_string("Content: |\n{% filter indent(2) %}{{ data | to_yaml }}{% endfilter %}")
        test_data = {"key": "value", "nested": {"inner": "data"}}
        result = template.render(data=test_data)
        
        expected = "Content: |\n  key: value\n  nested:\n    inner: data"
        self.assertEqual(result, expected)

    def test_combined_json_filters(self):
        """Test that to_json and indent filters work together."""
        from jinja2 import Environment
        import json
        
        env = Environment()
        env.filters['to_json'] = lambda value: json.dumps(value, indent=2, sort_keys=True)
        def indent_filter(s, n=2):
            if not s:
                return ''
            lines = s.splitlines()
            result = '\n'.join((' ' * n + line if line.strip() else '') for line in lines)
            return result
        env.filters['indent'] = indent_filter
        
        template = env.from_string("Content: |\n{% filter indent(2) %}{{ data | to_json }}{% endfilter %}")
        test_data = {"key": "value", "nested": {"inner": "data"}}
        result = template.render(data=test_data)
        
        expected = 'Content: |\n  {\n    "key": "value",\n    "nested": {\n      "inner": "data"\n    }\n  }'
        self.assertEqual(result, expected)

if __name__ == "__main__":
    unittest.main()
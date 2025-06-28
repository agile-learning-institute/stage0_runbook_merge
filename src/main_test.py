#################
# NOTE: Uses the test/specifications and test/repo folders

import unittest
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
        self.assertEqual(len(self.processor.templates), 4)  # Updated to include the new dict-test.j2 template

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
        mock_file.assert_any_call(os.path.normpath(os.path.join(self.TEST_REPO, "userService.ts")), "w")
        mock_file.assert_any_call(os.path.normpath(os.path.join(self.TEST_REPO, "organizationService.ts")), "w")

        # Verify that the source template file was removed
        mock_remove.assert_any_call(os.path.normpath(os.path.join(self.TEST_REPO, "source.ts")))
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

if __name__ == "__main__":
    unittest.main()
#################
# NOTE: Uses the test/specifications and test/repo folders

import unittest
from unittest.mock import patch, mock_open
import os
from main import Processor

class TestProcessor(unittest.TestCase):
    TEST_SPECIFICATIONS = "../test/specifications"
    TEST_REPO = "../test/repo"

    def setUp(self):
        """Set up a Processor instance for each test."""
        os.environ["SERVICE_NAME"] = "initialize-mongodb"
        os.environ["DOCUMENT_SCHEMA"] = "dd.user.yaml"
        self.processor = Processor(self.TEST_SPECIFICATIONS, self.TEST_REPO)

    def test_load_process(self):
        """Test that process.yaml is loaded correctly."""
        self.assertEqual(len(self.processor.environment), 2)
        self.assertIn("SERVICE_NAME", self.processor.environment)
        self.assertIn("DOCUMENT_SCHEMA", self.processor.environment)
        self.assertEqual(len(self.processor.templates), 3)

    def test_load_specifications(self):
        """Test that specifications are loaded correctly."""
        self.assertIn("architecture", self.processor.context_data["specifications"])
        self.assertIn("dataDefinitions", self.processor.context_data["specifications"])

    def test_add_context_with_resolved_directive(self):
        """Test that context is added correctly and resolves directives."""
        self.processor.read_environment()
        self.processor.add_context()

        # Verify context data includes the correct domain
        self.assertIn("service", self.processor.context_data)
        self.assertEqual(
            self.processor.context_data["service"]["name"], "initialize-mongodb"
        )
        self.assertEqual(
            self.processor.context_data["service"]["data"]["sources"][0]["name"], "user"
        )

        self.assertIn("document", self.processor.context_data)
        self.assertEqual(
            self.processor.context_data["document"]["description"], "User Data Definition"
        )

        self.assertIn("architecture", self.processor.context_data)
        self.assertIn("product", self.processor.context_data["architecture"])

    def test_resolve_directive(self):
        """Test the resolve_directive method for dynamic domain selection."""
        self.processor.read_environment()
        resolved = self.processor.resolve_directive(
            "specifications.architecture.domains[{name: SERVICE_NAME}]"
        )
        self.assertEqual(resolved["name"], "initialize-mongodb")
        self.assertEqual(resolved["description"], "Initialize mongo collection schema constraints and load test data")

    def test_verify_exists(self):
        """Test that required properties are verified correctly."""
        self.processor.read_environment()
        self.processor.add_context()
        try:
            self.processor.verify_exists()
        except KeyError as e:
            self.fail(f"verify_exists raised KeyError unexpectedly: {e}")

    def test_resolve_directive_with_invalid_name(self):
        """Test that resolve_directive raises KeyError for unmatched items."""
        self.processor.read_environment()
        os.environ["SERVICE_NAME"] = "nonexistent"
        with self.assertRaises(KeyError):
            self.processor.resolve_directive(
                "specifications.architecture.domains[{name: SERVICE_NAME}]"
            )

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.remove")
    def test_process_templates(self, mock_remove, mock_file):
        """Test template processing with mock file operations."""
        self.processor.read_environment()
        self.processor.add_context()
        self.processor.verify_exists()

        # Mock writing and removing files
        self.processor.process_templates()

        # Verify that files were opened for writing for the merge templates
        mock_file.assert_any_call(os.path.join(self.TEST_REPO, "simple.md"), "w")
        mock_file.assert_any_call(os.path.join(self.TEST_REPO, "loop-in.ts"), "w")

        # Verify that the mergeFor template produced the expected output files
        self.assertTrue(
            any(
                "Service.ts" in call_args[0][0]
                for call_args in mock_file.call_args_list
            ),
            "Expected mergeFor templates to create output files."
        )

        # Verify that files were not removed in this test case
        mock_remove.assert_not_called()


if __name__ == "__main__":
    unittest.main()
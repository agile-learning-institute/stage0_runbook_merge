#################
# NOTE: Uses the test/specifications and test/repo folders

import unittest
from unittest.mock import patch, mock_open
import os
from main import Processor

class TestProcessor(unittest.TestCase):
    TEST_SPECIFICATIONS = "./test/specifications"
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
        self.assertEqual(len(self.processor.context), 3)
        self.assertEqual("architecture", self.processor.context[0]["key"])
        self.assertEqual("service", self.processor.context[1]["key"])
        self.assertEqual("data-source", self.processor.context[2]["key"])
        self.assertEqual(len(self.processor.requires), 8)
        self.assertEqual(len(self.processor.templates), 3)

    def test_load_specifications(self):
        """Test that specifications are loaded correctly."""
        self.assertIn("architecture", self.processor.context_data["specifications"])
        self.assertEqual("ProductSlug", self.processor.context_data["specifications"]["architecture"]["product"])
        self.assertIn("dataDefinitions", self.processor.context_data["specifications"])
        self.assertEqual("User Object", self.processor.context_data["specifications"]["dataDefinitions"]["dd.user"]["title"])

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
    def test_process_templates(self, mock_remove, mock_file):
        """Test template processing with mock file operations."""
        self.processor.read_environment()
        self.processor.add_context()
        self.processor.verify_exists()

        # Mock writing and removing files
        self.processor.process_templates()

        # Verify that files were opened for writing for the merge templates
        mock_file.assert_any_call(os.path.normpath(os.path.join(self.TEST_REPO, "simple.md")), "w")
        mock_file.assert_any_call(os.path.normpath(os.path.join(self.TEST_REPO, "loop-in.ts")), "w")
        mock_file.assert_any_call(os.path.normpath(os.path.join(self.TEST_REPO, "userService.ts")), "w")
        mock_file.assert_any_call(os.path.normpath(os.path.join(self.TEST_REPO, "organizationService.ts")), "w")

        # Verify that the source template was removed
        mock_remove.assert_called_once()


if __name__ == "__main__":
    unittest.main()
#################
# NOTE: Uses the test/specifications and test/repo folders

import unittest
from unittest.mock import patch, mock_open
import os
import shutil
from main import Processor

class TestProcessor(unittest.TestCase):
    TEST_SPECIFICATIONS = "./test/specifications"
    TEST_REPO = "./test/repo_temp"

    def setUp(self):
        """Set up a Processor instance for each test."""
        os.environ["SERVICE_NAME"] = "TestService"
        self.processor = Processor(self.TEST_SPECIFICATIONS, self.TEST_REPO)

    def test_load_process(self):
        """Test that process.yaml is loaded correctly."""
        self.assertEqual(self.processor.environment, ["SERVICE_NAME"])
        self.assertEqual(len(self.processor.templates), 1)
        self.assertEqual(self.processor.templates[0]["path"], "simple_template.md")
        self.assertEqual(self.processor.templates[0]["merge"], True)

    def test_load_specifications(self):
        """Test that specifications are loaded correctly."""
        self.assertIn("architecture", self.processor.context_data["specifications"])
        self.assertEqual(
            self.processor.context_data["specifications"]["architecture"]["product"],
            "TestProduct"
        )
        self.assertEqual(
            self.processor.context_data["specifications"]["dataDefinitions"]["dd.user"]["description"],
            "User Data Definition"
        )

    def test_add_context(self):
        """Test that context is added correctly."""
        self.processor.read_environment()
        self.processor.add_context()
        self.assertIn("service", self.processor.context_data)
        self.assertEqual(self.processor.context_data["service"], "TestProduct")

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
        
        # Verify that files were opened for writing
        mock_file.assert_called_with(os.path.join(self.TEST_REPO, "simple_template.md"), "w")
        
        # Verify that file content was written correctly
        handle = mock_file()
        handle.write.assert_called_once_with("Service Name: TestProduct")
        
        # Verify that files were not removed in this test case
        mock_remove.assert_not_called()

if __name__ == "__main__":
    unittest.main()
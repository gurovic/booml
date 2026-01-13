from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
import tempfile
import os
from unittest.mock import patch

from ..utils.csv_utils import detect_csv_delimiter, read_csv_with_auto_delimiter, read_csv_file_with_auto_delimiter
from ..services.prevalidation_service import run_prevalidation
from ..models import Submission, Problem, ProblemDescriptor


class TestCSVDelimiterDetection(TestCase):
    def setUp(self):
        # Create a test problem and descriptor
        self.problem = Problem.objects.create(title="Test Problem", statement="Test statement")
        self.descriptor = ProblemDescriptor.objects.create(
            problem=self.problem,
            id_column="id",
            target_column="target",
            target_type="float"
        )

    def test_detect_comma_delimiter(self):
        """Test detection of comma delimiter"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,target\n1,0.5\n2,0.7\n")
            temp_path = f.name

        try:
            delimiter = detect_csv_delimiter(temp_path)
            self.assertEqual(delimiter, ',')
        finally:
            os.unlink(temp_path)

    def test_detect_semicolon_delimiter(self):
        """Test detection of semicolon delimiter"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id;target\n1;0.5\n2;0.7\n")
            temp_path = f.name

        try:
            delimiter = detect_csv_delimiter(temp_path)
            self.assertEqual(delimiter, ';')
        finally:
            os.unlink(temp_path)

    def test_detect_tab_delimiter(self):
        """Test detection of tab delimiter"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id\ttarget\n1\t0.5\n2\t0.7\n")
            temp_path = f.name

        try:
            delimiter = detect_csv_delimiter(temp_path)
            self.assertEqual(delimiter, '\t')
        finally:
            os.unlink(temp_path)

    def test_read_csv_with_different_delimiters(self):
        """Test reading CSV files with different delimiters"""
        # Test comma
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,target\n1,0.5\n2,0.7\n")
            comma_path = f.name

        try:
            data = read_csv_with_auto_delimiter(comma_path)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]['id'], '1')
            self.assertEqual(data[0]['target'], '0.5')
        finally:
            os.unlink(comma_path)

        # Test semicolon
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id;target\n1;0.5\n2;0.7\n")
            semicolon_path = f.name

        try:
            data = read_csv_with_auto_delimiter(semicolon_path)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]['id'], '1')
            self.assertEqual(data[0]['target'], '0.5')
        finally:
            os.unlink(semicolon_path)

    def test_read_uploaded_csv_with_different_delimiters(self):
        """Test reading uploaded CSV files with different delimiters"""
        # Create a comma-separated file
        csv_content = "id,target\n1,0.5\n2,0.7\n"
        uploaded_file = SimpleUploadedFile("test.csv", csv_content.encode('utf-8'), content_type="text/csv")
        
        data = read_csv_file_with_auto_delimiter(uploaded_file)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['id'], '1')
        self.assertEqual(data[0]['target'], '0.5')

        # Create a semicolon-separated file
        csv_content = "id;target\n1;0.5\n2;0.7\n"
        uploaded_file = SimpleUploadedFile("test.csv", csv_content.encode('utf-8'), content_type="text/csv")
        
        data = read_csv_file_with_auto_delimiter(uploaded_file)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['id'], '1')
        self.assertEqual(data[0]['target'], '0.5')

    @patch('..services.prevalidation_service._finalize_report')
    def test_prevalidation_with_different_delimiters(self, mock_finalize):
        """Test that prevalidation works with different delimiters"""
        # Mock the finalize function to return a simple object
        from unittest.mock import MagicMock
        mock_result = MagicMock()
        mock_result.errors_count = 0
        mock_finalize.return_value = mock_result
        
        # Create a submission with a semicolon-delimited file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id;target\n1;0.5\n2;0.7\n")
            temp_path = f.name

        try:
            # Create a submission
            from django.contrib.auth.models import User
            user = User.objects.create_user(username='testuser')
            
            submission = Submission.objects.create(
                user=user,
                problem=self.problem,
                file=temp_path
            )
            
            # This should work without errors due to delimiter detection
            result = run_prevalidation(submission)
            # The test passes if no exception is raised
        finally:
            os.unlink(temp_path)
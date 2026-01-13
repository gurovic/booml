import csv
import io
from typing import Optional, Dict, Any, List
from django.core.files.uploadedfile import UploadedFile


def detect_csv_delimiter(file_path_or_content: str, sample_size: int = 1024) -> str:
    """
    Automatically detect the delimiter of a CSV file.
    
    Args:
        file_path_or_content: Either a file path or file content as string
        sample_size: Number of bytes to read for delimiter detection
    
    Returns:
        Detected delimiter character
    """
    sniffer = csv.Sniffer()
    
    # If it's a file path, read the file
    if isinstance(file_path_or_content, str) and len(file_path_or_content) > 0 and file_path_or_content[0] != '{':
        with open(file_path_or_content, 'r', encoding='utf-8', newline='') as f:
            sample = f.read(sample_size)
    else:
        # Assume it's content
        sample = file_path_or_content
    
    # Detect the delimiter
    delimiter = sniffer.sniff(sample, delimiters=',;\t|: ').delimiter
    return delimiter


def read_csv_with_auto_delimiter(file_path: str, **kwargs) -> List[Dict[str, Any]]:
    """
    Read a CSV file with automatic delimiter detection.
    
    Args:
        file_path: Path to the CSV file
        **kwargs: Additional arguments to pass to csv.DictReader
    
    Returns:
        List of dictionaries representing CSV rows
    """
    delimiter = detect_csv_delimiter(file_path)
    
    with open(file_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f, delimiter=delimiter, **kwargs)
        return list(reader)


def read_csv_file_with_auto_delimiter(uploaded_file: UploadedFile, **kwargs) -> List[Dict[str, Any]]:
    """
    Read an uploaded CSV file with automatic delimiter detection.
    
    Args:
        uploaded_file: Django UploadedFile object
        **kwargs: Additional arguments to pass to csv.DictReader
    
    Returns:
        List of dictionaries representing CSV rows
    """
    # Seek to the beginning of the file
    uploaded_file.seek(0)
    
    # Read the content
    content = uploaded_file.read().decode('utf-8')
    uploaded_file.seek(0)  # Reset for any further processing
    
    # Detect delimiter from content
    sniffer = csv.Sniffer()
    sample = content[:1024]  # Sample first 1024 characters
    delimiter = sniffer.sniff(sample, delimiters=',;\t|: ').delimiter
    
    # Parse the CSV content
    f = io.StringIO(content)
    reader = csv.DictReader(f, delimiter=delimiter, **kwargs)
    return list(reader)


def write_csv_with_delimiter(data: List[Dict[str, Any]], delimiter: str = ',', **kwargs) -> str:
    """
    Write data to CSV format with specified delimiter.
    
    Args:
        data: List of dictionaries to write to CSV
        delimiter: Delimiter to use in the CSV
        **kwargs: Additional arguments to pass to csv.DictWriter
    
    Returns:
        String representation of the CSV content
    """
    if not data:
        return ""
    
    output = io.StringIO()
    fieldnames = list(data[0].keys()) if data else []
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=delimiter, **kwargs)
    writer.writeheader()
    writer.writerows(data)
    
    return output.getvalue()


def validate_csv_structure(file_path: str, required_columns: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Validate CSV structure with automatic delimiter detection.
    
    Args:
        file_path: Path to the CSV file
        required_columns: List of required column names
    
    Returns:
        Dictionary with validation results
    """
    delimiter = detect_csv_delimiter(file_path)
    
    with open(file_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        headers = reader.fieldnames
        
        if headers is None:
            return {
                'valid': False,
                'error': 'Could not read headers from CSV file',
                'delimiter': delimiter
            }
        
        if required_columns:
            missing_columns = [col for col in required_columns if col not in headers]
            if missing_columns:
                return {
                    'valid': False,
                    'error': f'Missing required columns: {missing_columns}',
                    'delimiter': delimiter,
                    'available_columns': list(headers)
                }
    
    return {
        'valid': True,
        'delimiter': delimiter,
        'columns': list(headers) if headers else [],
        'total_rows': sum(1 for _ in csv.DictReader(open(file_path, 'r', encoding='utf-8', newline=''), delimiter=delimiter))
    }
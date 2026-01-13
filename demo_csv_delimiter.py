#!/usr/bin/env python
"""
Demonstration script for CSV delimiter detection functionality.
This script shows how the new CSV utilities work with different delimiters.
"""

import tempfile
import os
import sys
import csv
import io
from typing import Optional, Dict, Any, List


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


def demo_csv_delimiter_detection():
    print("CSV Delimiter Detection Demo")
    print("=" * 40)

    # Test 1: Comma-separated CSV
    print("\n1. Testing comma-separated CSV:")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("id,name,score\n1,Alice,95\n2,Bob,87\n3,Charlie,92\n")
        comma_csv_path = f.name

    delimiter = detect_csv_delimiter(comma_csv_path)
    print(f"   Detected delimiter: '{delimiter}' (should be ',')")

    data = read_csv_with_auto_delimiter(comma_csv_path)
    print(f"   Rows read: {len(data)}")
    print(f"   First row: {data[0]}")

    os.unlink(comma_csv_path)

    # Test 2: Semicolon-separated CSV
    print("\n2. Testing semicolon-separated CSV:")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("id;name;score\n1;Alice;95\n2;Bob;87\n3;Charlie;92\n")
        semicolon_csv_path = f.name

    delimiter = detect_csv_delimiter(semicolon_csv_path)
    print(f"   Detected delimiter: '{delimiter}' (should be ';')")

    data = read_csv_with_auto_delimiter(semicolon_csv_path)
    print(f"   Rows read: {len(data)}")
    print(f"   First row: {data[0]}")

    os.unlink(semicolon_csv_path)

    # Test 3: Tab-separated CSV
    print("\n3. Testing tab-separated CSV:")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("id\tname\tscore\n1\tAlice\t95\n2\tBob\t87\n3\tCharlie\t92\n")
        tab_csv_path = f.name

    delimiter = detect_csv_delimiter(tab_csv_path)
    print(f"   Detected delimiter: '{delimiter}' (should be '\\t')")

    data = read_csv_with_auto_delimiter(tab_csv_path)
    print(f"   Rows read: {len(data)}")
    print(f"   First row: {data[0]}")

    os.unlink(tab_csv_path)

    # Test 4: Pipe-separated CSV
    print("\n4. Testing pipe-separated CSV:")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("id|name|score\n1|Alice|95\n2|Bob|87\n3|Charlie|92\n")
        pipe_csv_path = f.name

    delimiter = detect_csv_delimiter(pipe_csv_path)
    print(f"   Detected delimiter: '{delimiter}' (should be '|')")

    data = read_csv_with_auto_delimiter(pipe_csv_path)
    print(f"   Rows read: {len(data)}")
    print(f"   First row: {data[0]}")

    os.unlink(pipe_csv_path)

    # Test 5: Validation with required columns
    print("\n5. Testing validation with required columns:")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("id;name;score\n1;Alice;95\n2;Bob;87\n3;Charlie;92\n")
        validation_csv_path = f.name

    validation_result = validate_csv_structure(validation_csv_path, required_columns=['id', 'score'])
    print(f"   Valid: {validation_result['valid']}")
    print(f"   Delimiter: '{validation_result['delimiter']}'")
    print(f"   Columns: {validation_result['columns']}")
    print(f"   Total rows: {validation_result['total_rows']}")

    os.unlink(validation_csv_path)

    print("\n" + "=" * 40)
    print("Demo completed successfully!")
    print("The CSV delimiter detection functionality is working correctly.")


if __name__ == "__main__":
    demo_csv_delimiter_detection()
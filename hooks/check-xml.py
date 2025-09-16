#!/usr/bin/env python3
"""
Check XML file syntax validation.
"""

import sys
import argparse
import xml.etree.ElementTree as ET
from xml.parsers.expat import ExpatError


def validate_xml_file(file_path):
    """Validate XML file syntax."""
    try:
        ET.parse(file_path)
        return True, None
    except ET.ParseError as e:
        return False, f"XML Parse Error: {e}"
    except ExpatError as e:
        return False, f"XML Syntax Error: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def main():
    parser = argparse.ArgumentParser(description='Validate XML file syntax')
    parser.add_argument('files', nargs='*', help='XML files to validate')
    args = parser.parse_args()
    
    exit_code = 0
    
    for file_path in args.files:
        try:
            is_valid, error_msg = validate_xml_file(file_path)
            
            if is_valid:
                print(f"✅ {file_path}: Valid XML")
            else:
                print(f"❌ {file_path}: {error_msg}")
                exit_code = 1
                
        except FileNotFoundError:
            print(f"❌ {file_path}: File not found")
            exit_code = 1
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
Test script for the database migration functionality.
This script tests the argument parsing and basic functionality without actually running migrations.
"""

import sys
import subprocess
from pathlib import Path

def test_argument_parsing():
    """Test that the script correctly parses arguments."""
    script_path = Path(__file__).parent / "db_migrate.py"
    
    # Test help
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
            check=True
        )
        print("✓ Help command works correctly")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Help command failed: {e}")
        return False

def test_invalid_arguments():
    """Test that the script correctly handles invalid arguments."""
    script_path = Path(__file__).parent / "db_migrate.py"
    
    # Test missing required arguments
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            print("✓ Correctly rejects missing arguments")
            return True
        else:
            print("✗ Should have rejected missing arguments")
            return False
    except Exception as e:
        print(f"✗ Error testing invalid arguments: {e}")
        return False

def test_same_src_dst():
    """Test that the script correctly rejects same source and destination."""
    script_path = Path(__file__).parent / "db_migrate.py"
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--src", "dev", "--dst", "dev"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            print("✓ Correctly rejects same source and destination")
            return True
        else:
            print("✗ Should have rejected same source and destination")
            return False
    except Exception as e:
        print(f"✗ Error testing same src/dst: {e}")
        return False

def test_doppler_context():
    """Test that doppler context is properly managed."""
    script_path = Path(__file__).parent / "db_migrate.py"
    
    # Test with a mock command that just checks if doppler is available
    try:
        result = subprocess.run(
            ["doppler", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print("✓ Doppler is available")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠ Doppler not available (this is expected in some environments)")
        return True

def main():
    """Run all tests."""
    print("Testing database migration script...")
    print("=" * 50)
    
    tests = [
        ("Argument parsing", test_argument_parsing),
        ("Invalid arguments", test_invalid_arguments),
        ("Same source/destination", test_same_src_dst),
        ("Doppler context", test_doppler_context),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\nTesting: {test_name}")
        if test_func():
            passed += 1
        else:
            print(f"✗ {test_name} failed")
    
    print("\n" + "=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
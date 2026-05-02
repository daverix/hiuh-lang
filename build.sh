#!/bin/bash

set -e # Exit immediately if a command exits with a non-zero status.

echo "========================================"
echo "Starting Hiue Compiler Build and Test Process"
echo "========================================"

# 1. Environment Setup (Optional: Activate virtual environment if applicable)
# source venv/bin/activate

# 2. Testing the Code
echo -e "\n--- Running Tests ---"
# Assuming 'pytest' is installed and available to run tests from the 'tests/' directory.
# If a different test runner is used, this command must be updated.
if command -v pytest &> /dev/null; then
    pytest tests/
else
    echo "Warning: pytest not found. Skipping automated testing."
    # Fallback test execution if pytest is not installed/available
    # Example: python -m unittest discover tests
fi

# 3. Compilation/Code Check (Placeholder for pre-build steps if needed)
echo -e "\n--- Running Pre-Build Checks ---"
# Add any linter checks or static analysis tools here (e.g., flake8)
# Ex: flake8 src/

echo -e "\n========================================"
echo "Build and Test process completed successfully!"
echo "========================================"
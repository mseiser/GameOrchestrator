# Run tests for Game Orchestrator
# Usage:
#   .\run_tests.ps1

# Set PYTHONPATH to include the project root
$env:PYTHONPATH = $PWD

python -m unittest discover -s tests -p "test_*.py"
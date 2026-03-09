# Run tests for Game Orchestrator
# Usage:
#   .\run_tests.ps1

# Set PYTHONPATH to include the project root
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = $projectRoot
Set-Location $projectRoot

python -m unittest discover -s tests -p "test_*.py"
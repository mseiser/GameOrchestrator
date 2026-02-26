# Temporary HTTP-only server for testing Unity connectivity
# DO NOT USE IN PRODUCTION

param(
    [string]$HostIP = "0.0.0.0",
    [int]$Port = 8000
)

Write-Host "==== Starting HTTP-only Game Orchestrator (TEST MODE) ===="
Write-Host "WARNING: Running without TLS - for testing only!"
Write-Host ""

# Activate virtual environment
& ".\.venv\Scripts\Activate.ps1"

# Load environment variables
if (Test-Path ".\.env") {
    Get-Content .\.env | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value)
        }
    }
}

Write-Host "Host: $HostIP"
Write-Host "Port: $Port"
Write-Host "API Documentation: http://$($HostIP):$Port/docs"
Write-Host ""

python -m uvicorn api:app --host $HostIP --port $Port --reload

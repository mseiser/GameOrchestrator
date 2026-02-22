# Game Orchestrator API Startup Script
# Run to host the API server with optional debug and reload settings.
# Usage:
#   .\run_app.ps1
#   .\run_app.ps1 -HostIP 
#   .\run_app.ps1 -HostIP <IP_ADDRESS> -Port 8080
#   .\run_app.ps1 -Debug -DebugPort 5678 -DebugWait

param(
    [switch]$NoReload = $false,
    [string]$HostIP = "0.0.0.0",
    [int]$Port = 8000,
    [switch]$Debug = $false,
    [int]$DebugPort = 5678,
    [switch]$DebugWait = $false
)

Write-Host "==== Game Orchestrator Setup ===="

# Check if virtual environment exists
if (-not (Test-Path ".\.venv")) {
    Write-Host "Virtual environment not found. Creating one..."
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment"
        exit 1
    }
}

# Activate virtual environment
Write-Host "Activating virtual environment..."
& ".\\.venv\\Scripts\\Activate.ps1"

# Install/update requirements
Write-Host "Installing dependencies..."
pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install requirements"
    exit 1
}

if ($Debug) {
    Write-Host "Installing debugpy..."
    pip install -q debugpy
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install debugpy"
        exit 1
    }
}

# Load environment variables
Write-Host "Loading environment configuration..."
if (-not (Test-Path ".\.env")) {
    Write-Warning ".env file not found. Continuing without environment variables."
    Write-Host "Please create .env file with DB_PATH and other required variables."
}
else {
    Get-Content .\.env | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value)
        }
    }
}

# Create database if not exists
Write-Host "Checking database..."
$dbPath = [Environment]::GetEnvironmentVariable("DB_PATH")
if ($dbPath -and -not (Test-Path $dbPath)) {
    Write-Host "Database not found at $dbPath. Creating..."
    python db\database_setup.py
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create database"
        exit 1
    }
    Write-Host "Database created successfully."
}

# Display startup information
Write-Host ""
Write-Host "==== Starting Game Orchestrator API ===="
Write-Host "Host: $HostIP"
Write-Host "Port: $Port"
if ($NoReload) {
    Write-Host "Auto-reload: Disabled"
}
else {
    Write-Host "Auto-reload: Enabled"
}
if ($Debug) {
    Write-Host "Debug: Enabled (port $DebugPort)"
    if ($DebugWait) {
        Write-Host "Debug: Waiting for client before start"
    }
}
Write-Host "API Documentation: http://{$HostIP}:$Port/docs"
Write-Host ""

# Start the server
$uvicornArgs = @("api:app")
if (-not $NoReload) {
    $uvicornArgs += "--reload"
}
$uvicornArgs += @("--host", $HostIP, "--port", $Port)

if ($Debug) {
    $debugArgs = @("--listen", "127.0.0.1:$DebugPort")
    if ($DebugWait) {
        $debugArgs += "--wait-for-client"
    }
    python -m debugpy @debugArgs -m uvicorn @uvicornArgs
}
else {
    python -m uvicorn @uvicornArgs
}
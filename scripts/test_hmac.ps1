# HMAC Signature Calculator
# Calculates HMAC signature and body hash for given inputs

param(
    [Parameter(Mandatory = $false)]
    [string]$Timestamp = "",
    
    [Parameter(Mandatory = $false)]
    [string]$Body = '{"droplet_ip": "192.168.1.100", "connected_clients": 2}',
    
    [Parameter(Mandatory = $false)]
    [string]$Method = "POST",
    
    [Parameter(Mandatory = $false)]
    [string]$Path = "/server/heartbeat",
    
    [Parameter(Mandatory = $false)]
    [string]$Query = "",
    
    [Parameter(Mandatory = $false)]
    [string]$HmacKey = ""
)

Write-Host "==== HMAC Signature Calculator ====" -ForegroundColor Cyan
Write-Host ""

# Load HMAC key from .env if not provided
if ([string]::IsNullOrWhiteSpace($HmacKey)) {
    if (Test-Path ".\.env") {
        Get-Content .\.env | ForEach-Object {
            if ($_ -match '^\s*INTERNAL_HMAC_KEY\s*=\s*(.*)$') {
                $HmacKey = $matches[1].Trim()
            }
        }
    }
    
    if ([string]::IsNullOrWhiteSpace($HmacKey)) {
        Write-Error "HMAC key not found. Provide -HmacKey parameter or set INTERNAL_HMAC_KEY in .env"
        exit 1
    }
}

# Generate timestamp if not provided
if ([string]::IsNullOrWhiteSpace($Timestamp)) {
    $Timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds().ToString()
    Write-Host "Generated Timestamp: $Timestamp" -ForegroundColor Yellow
}
else {
    Write-Host "Using Provided Timestamp: $Timestamp" -ForegroundColor Yellow
}
Write-Host ""

# Convert body to bytes and compute SHA256 hash
$bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($Body)
$sha256 = [System.Security.Cryptography.SHA256]::Create()
$bodyHashBytes = $sha256.ComputeHash($bodyBytes)
$bodyHash = [System.BitConverter]::ToString($bodyHashBytes) -replace '-', ''
$bodyHash = $bodyHash.ToLower()

# Build HMAC message (must match Python's _build_hmac_message)
$hmacMessage = @(
    $Method.ToUpper(),
    $Path,
    $Query,
    $Timestamp,
    $bodyHash
) -join "`n"

# Compute HMAC signature
$hmacKeyBytes = [System.Text.Encoding]::UTF8.GetBytes($HmacKey)
$hmacMessageBytes = [System.Text.Encoding]::UTF8.GetBytes($hmacMessage)
$hmac = [System.Security.Cryptography.HMACSHA256]::new($hmacKeyBytes)
$signatureBytes = $hmac.ComputeHash($hmacMessageBytes)
$signature = [System.BitConverter]::ToString($signatureBytes) -replace '-', ''
$signature = $signature.ToLower()

# Output Results
Write-Host "=== Input ===" -ForegroundColor Yellow
Write-Host "Method:    $Method"
Write-Host "Path:      $Path"
Write-Host "Query:     $Query"
Write-Host "Timestamp: $Timestamp"
Write-Host "Body:      $Body"
Write-Host "Body Len:  $($bodyBytes.Length) bytes"
Write-Host ""

Write-Host "=== HMAC Message (newline-separated) ===" -ForegroundColor Magenta
Write-Host "---"
Write-Host $hmacMessage
Write-Host "---"
Write-Host ""

Write-Host "=== Output ===" -ForegroundColor Green
Write-Host "Body Hash (SHA256): $bodyHash"
Write-Host "HMAC Signature:     $signature"
Write-Host ""

Write-Host "=== Headers to use ===" -ForegroundColor Cyan
Write-Host "Request-Timestamp: $Timestamp"
Write-Host "Request-Signature: $signature"

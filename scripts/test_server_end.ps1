param(
    [string]$BaseUrl = "https://localhost:8000",
    [string]$DropletIp = "10.0.0.1",
    [string]$EnvFile = "",
    [switch]$Insecure
)

$ErrorActionPreference = "Stop"

function Import-DotEnv {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return
    }

    Get-Content $Path | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value)
        }
    }
}

function Resolve-EnvFilePath {
    param([string]$ConfiguredEnvFile)

    if (-not [string]::IsNullOrWhiteSpace($ConfiguredEnvFile)) {
        if ([System.IO.Path]::IsPathRooted($ConfiguredEnvFile)) {
            return $ConfiguredEnvFile
        }
        return (Join-Path -Path (Get-Location) -ChildPath $ConfiguredEnvFile)
    }

    return (Join-Path -Path $PSScriptRoot -ChildPath ".env")
}

function Get-Sha256Hex {
    param([byte[]]$Bytes)
    $hashBytes = [System.Security.Cryptography.SHA256]::HashData($Bytes)
    return ([System.BitConverter]::ToString($hashBytes) -replace '-', '').ToLowerInvariant()
}

function Get-HmacSha256Hex {
    param(
        [string]$Secret,
        [string]$Message
    )

    $secretBytes = [System.Text.Encoding]::UTF8.GetBytes($Secret)
    $messageBytes = [System.Text.Encoding]::UTF8.GetBytes($Message)
    $hmac = [System.Security.Cryptography.HMACSHA256]::new($secretBytes)
    try {
        $hashBytes = $hmac.ComputeHash($messageBytes)
        return ([System.BitConverter]::ToString($hashBytes) -replace '-', '').ToLowerInvariant()
    }
    finally {
        $hmac.Dispose()
    }
}

$resolvedEnvFile = Resolve-EnvFilePath -ConfiguredEnvFile $EnvFile
Import-DotEnv -Path $resolvedEnvFile

$hmacKey = [Environment]::GetEnvironmentVariable("INTERNAL_HMAC_KEY")
if ([string]::IsNullOrWhiteSpace($hmacKey)) {
    throw "Missing INTERNAL_HMAC_KEY in environment."
}

$method = "POST"
$path = "/server/end"
$query = "droplet_ip=$([uri]::EscapeDataString($DropletIp))"
$timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds().ToString()
$bodyBytes = [System.Text.Encoding]::UTF8.GetBytes("")
$bodyHash = Get-Sha256Hex -Bytes $bodyBytes
$message = "$method`n$path`n$query`n$timestamp`n$bodyHash"
$signature = Get-HmacSha256Hex -Secret $hmacKey -Message $message

$headers = @{
    "Request-Timestamp" = $timestamp
    "Request-Signature" = $signature
}

$url = "$($BaseUrl.TrimEnd('/'))$path`?$query"

$invokeParams = @{
    Uri         = $url
    Method      = "Post"
    Headers     = $headers
    ErrorAction = "Stop"
}
if ($Insecure) {
    $invokeParams["SkipCertificateCheck"] = $true
}

$response = Invoke-WebRequest @invokeParams
Write-Host "HTTP $($response.StatusCode)"
Write-Output $response.Content

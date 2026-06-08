param(
    [string]$RemoteTarget = "root@femquestorchestrator.mariasgames.xyz:/orchestrator",
    [string]$ArchiveName = "app.tar"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$stagingRoot = Join-Path $env:TEMP ("app" + [guid]::NewGuid().ToString("N"))
$stagingApp = Join-Path $stagingRoot "app"
$archivePath = Join-Path $repoRoot $ArchiveName

function Assert-CommandExists {
    param(
        [string]$Name
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found in PATH."
    }
}

try {
    Assert-CommandExists -Name "tar"
    Assert-CommandExists -Name "scp"
    Assert-CommandExists -Name "ssh"

    $remoteParts = $RemoteTarget -split ":", 2
    if ($remoteParts.Count -ne 2 -or [string]::IsNullOrWhiteSpace($remoteParts[0]) -or [string]::IsNullOrWhiteSpace($remoteParts[1])) {
        throw "RemoteTarget must be in the form user@host:/remote/path"
    }

    $remoteHost = $remoteParts[0]
    $remotePath = $remoteParts[1]
    $remoteArchivePath = ($remotePath.TrimEnd('/') + '/' + $ArchiveName)

    $requiredPaths = @(
        (Join-Path $repoRoot "Caddyfile"),
        (Join-Path $repoRoot "docker-compose.yml"),
        (Join-Path $repoRoot ".env"),
        (Join-Path $repoRoot "app")
    )

    foreach ($path in $requiredPaths) {
        if (-not (Test-Path $path)) {
            throw "Required path not found: $path"
        }
    }

    if (Test-Path $stagingRoot) {
        Remove-Item -Recurse -Force $stagingRoot
    }

    New-Item -ItemType Directory -Force -Path $stagingApp | Out-Null

    Copy-Item (Join-Path $repoRoot "Caddyfile") -Destination $stagingRoot
    Copy-Item (Join-Path $repoRoot "docker-compose.yml") -Destination $stagingRoot
    Copy-Item (Join-Path $repoRoot ".env") -Destination $stagingRoot
    Copy-Item (Join-Path $repoRoot "app\*") -Destination $stagingApp -Recurse -Force

    if (Test-Path $archivePath) {
        Remove-Item -Force $archivePath
    }

    Push-Location $stagingRoot
    try {
        tar -cf $archivePath "Caddyfile" "docker-compose.yml" ".env" "app"
    }
    finally {
        Pop-Location
    }

    Write-Host "Created archive: $archivePath"
    Write-Host "Uploading to: $RemoteTarget"

    scp $archivePath $RemoteTarget

    ssh $remoteHost "mkdir -p '$remotePath' && tar -xf '$remoteArchivePath' -C '$remotePath' && rm -f '$remoteArchivePath'"

    Write-Host "Deploy archive uploaded successfully."
}
finally {
    if (Test-Path $stagingRoot) {
        Remove-Item -Recurse -Force $stagingRoot
    }
}
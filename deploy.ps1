<#
.SYNOPSIS
    Packages the app/ folder and deploys it to the orchestrator host.
#>

param(
    [string]$RemoteHost = "root@orchestrator.physicsquest.xyz",
    [string]$RemoteDir = "/../orchestrator",
    [string]$LocalArchive = "app.tar",
    [string]$LocalAppFolder = "app"
)

$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [string]$Description,
        [scriptblock]$Action
    )

    Write-Host "==> $Description" -ForegroundColor Cyan
    $global:LASTEXITCODE = 0
    & $Action
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Step failed: $Description (exit code $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Invoke-Step "Removing existing $LocalArchive" {
    if (Test-Path $LocalArchive) {
        Remove-Item $LocalArchive -Force
    }
}

Invoke-Step "Creating $LocalArchive from $LocalAppFolder/ contents" {
    tar -cf $LocalArchive -C $LocalAppFolder .
}

Invoke-Step "Copying $LocalArchive to ${RemoteHost}:${RemoteDir}" {
    scp $LocalArchive "${RemoteHost}:${RemoteDir}/app.tar"
}

Invoke-Step "Replacing remote app folder and extracting archive" {
    ssh $RemoteHost "cd $RemoteDir && rm -rf app && mkdir app && tar -xf app.tar -C app"
}

Invoke-Step "Restarting containers (docker compose down / up --build)" {
    ssh $RemoteHost "cd $RemoteDir && docker compose down && docker compose up -d --build"
}

Invoke-Step "Fetching recent logs" {
    ssh $RemoteHost "cd $RemoteDir && docker compose logs --tail=100"
}

Write-Host "Deploy complete. Follow live logs with:" -ForegroundColor Green
Write-Host "  ssh $RemoteHost `"cd $RemoteDir && docker compose logs -f`""

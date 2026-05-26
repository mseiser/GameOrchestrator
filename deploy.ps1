param(
    [string]$RemoteServer = "root@femquestorchestrator.mariasgames.xyz",
    [string]$RemotePath = "/orchestrator",
    [int]$SshPort = 22,
    [switch]$UseSudo,
    [switch]$SkipEnvFile,
    [switch]$StopExisting,
    [switch]$ForceRecreate
)

$ErrorActionPreference = "Stop"

function Invoke-RemoteCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Command
    )

    $sshArgs = @()
    if ($SshPort -and $SshPort -ne 22) {
        $sshArgs += '-p'
        $sshArgs += $SshPort
    }
    $sshArgs += $RemoteServer
    $sshArgs += $Command

    $output = & ssh @sshArgs 2>&1
    $exit = $LASTEXITCODE
    if ($exit -ne 0) {
        $msg = $output -join "`n"
        throw "Remote command failed: $Command`n$msg"
    }
}

function Copy-LocalPathToRemote {
    param(
        [Parameter(Mandatory = $true)][string]$LocalPath,
        [Parameter(Mandatory = $true)][string]$TargetPath
    )

    $SourcePath = Join-Path $projectRoot $LocalPath
    $scpArgs = @()
    if ($SshPort -and $SshPort -ne 22) {
        $scpArgs += '-P'
        $scpArgs += $SshPort
    }
    $scpArgs += '-r'
    $scpArgs += $SourcePath
    $scpArgs += "${RemoteServer}:$TargetPath"

    & scp @scpArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to copy $LocalPath to $TargetPath"
    }
}

$projectRoot = $PSScriptRoot
Set-Location $projectRoot

Write-Host "Deploying Game Orchestrator to ${RemoteServer}:$RemotePath"

Invoke-RemoteCommand "mkdir -p $RemotePath"

Copy-LocalPathToRemote -LocalPath "app" -TargetPath "$RemotePath/"
Copy-LocalPathToRemote -LocalPath "docker-compose.yml" -TargetPath "$RemotePath/"
Copy-LocalPathToRemote -LocalPath "Caddyfile" -TargetPath "$RemotePath/"

if (-not $SkipEnvFile -and (Test-Path ".env")) {
    Copy-LocalPathToRemote -LocalPath ".env" -TargetPath "$RemotePath/"
}
elseif (-not $SkipEnvFile) {
    Write-Warning ".env was not found locally, so it was not copied. Ensure the server already has $RemotePath/.env configured."
}

try {
        $sudoPrefix = if ($UseSudo) { 'sudo ' } else { '' }
        $forceArgs = if ($ForceRecreate) { '--force-recreate --build' } else { '--build' }

        Write-Host "Changing to remote directory: $RemotePath"
        Invoke-RemoteCommand "cd $RemotePath"

        if ($StopExisting) {
                Write-Host "Stopping existing compose stack on remote (if any)"
                $downCmd = "if docker compose version >/dev/null 2>&1; then $sudoPrefix docker compose down --remove-orphans || true; elif command -v docker-compose >/dev/null 2>&1; then $sudoPrefix docker-compose down --remove-orphans || true; else echo 'No compose binary found to stop' >&2; fi"
                Invoke-RemoteCommand "cd $RemotePath && $downCmd"
        }

        Write-Host "Starting docker compose on remote"
        $composeCmd = "if docker compose version >/dev/null 2>&1; then $sudoPrefix docker compose up -d $forceArgs; elif command -v docker-compose >/dev/null 2>&1; then $sudoPrefix docker-compose up -d $forceArgs; else echo 'No docker compose binary found on remote' >&2; exit 1; fi"
        Invoke-RemoteCommand "cd $RemotePath && $composeCmd"

}
catch {
        throw "Remote command failed: cd $RemotePath && docker compose up -d --build`n$($_.Exception.Message)"
}

Write-Host "Deployment completed successfully."
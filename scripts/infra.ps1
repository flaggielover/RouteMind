[CmdletBinding()]
param(
    [ValidateSet("up", "wait", "status", "logs", "down")]
    [string] $Action = "status",
    [ValidateRange(10, 600)]
    [int] $TimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$services = @("postgres", "rabbitmq", "redis")

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments)] [string[]] $Arguments)

    & docker compose @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Wait-Healthy {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $states = @{}
        foreach ($service in $services) {
            $containerId = (& docker compose ps -q $service).Trim()
            if ($LASTEXITCODE -ne 0) {
                throw "Unable to inspect Compose service $service"
            }
            if (-not $containerId) {
                $states[$service] = "missing"
                continue
            }
            $states[$service] = (& docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $containerId).Trim()
            if ($LASTEXITCODE -ne 0) {
                throw "Unable to inspect container for $service"
            }
        }

        $summary = ($services | ForEach-Object { "$_=$($states[$_])" }) -join ", "
        Write-Host "Infrastructure: $summary"
        if (@($states.Values | Where-Object { $_ -ne "healthy" }).Count -eq 0) {
            Write-Host "PASS: PostgreSQL, RabbitMQ, and Redis are healthy"
            return
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)

    Invoke-Compose -Arguments @("ps")
    Invoke-Compose -Arguments @("logs", "--tail", "100")
    throw "Infrastructure did not become healthy within $TimeoutSeconds seconds"
}

Push-Location $root
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker is required for local infrastructure"
    }
    Invoke-Compose -Arguments @("config", "--quiet")

    switch ($Action) {
        "up" {
            Invoke-Compose -Arguments @("up", "-d", "--pull", "missing")
            Wait-Healthy
        }
        "wait" {
            Wait-Healthy
        }
        "status" {
            Invoke-Compose -Arguments @("ps")
        }
        "logs" {
            Invoke-Compose -Arguments @("logs", "--tail", "200")
        }
        "down" {
            Invoke-Compose -Arguments @("down")
            Write-Host "Persistent development volumes were preserved"
        }
    }
}
finally {
    Pop-Location
}

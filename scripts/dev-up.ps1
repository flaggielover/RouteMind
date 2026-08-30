[CmdletBinding()]
param(
    [ValidateSet("check", "up", "status", "down")]
    [string] $Action = "up",
    [ValidateRange(15, 900)]
    [int] $TimeoutSeconds = 240,
    [switch] $SkipWeb
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path ([System.IO.Path]::GetTempPath()) "routemind-local-runtime"
$statePath = if ($env:ROUTEMIND_RUNTIME_STATE_PATH) {
    [System.IO.Path]::GetFullPath($env:ROUTEMIND_RUNTIME_STATE_PATH)
}
else {
    Join-Path $runtimeRoot "state.json"
}
$businessUri = "http://127.0.0.1:18080"
$computeUri = "http://127.0.0.1:18081"
$webUri = "http://127.0.0.1:4173"

function Get-PwshPath {
    $command = Get-Command pwsh -ErrorAction SilentlyContinue
    if (-not $command) {
        $command = Get-Command powershell -ErrorAction SilentlyContinue
    }
    if (-not $command) {
        throw "PowerShell is required to run the local lifecycle"
    }
    return $command.Source
}

function Assert-Tool([string] $Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is required for the local lifecycle"
    }
}

function Ensure-RuntimeDirectory {
    $directory = Split-Path -Parent $statePath
    if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
}

function Get-LogPath([string] $Service, [string] $Stream) {
    Ensure-RuntimeDirectory
    return Join-Path $runtimeRoot "$Service.$Stream.log"
}

function Ensure-EnvironmentFile {
    $envFile = Join-Path $root ".env"
    $example = Join-Path $root ".env.example"
    if (-not (Test-Path -LiteralPath $envFile -PathType Leaf)) {
        Copy-Item -LiteralPath $example -Destination $envFile
        Write-Host "Created .env from .env.example"
    }
    $required = @(
        "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_PORT",
        "RABBITMQ_DEFAULT_USER", "RABBITMQ_DEFAULT_PASS", "RABBITMQ_AMQP_PORT",
        "RABBITMQ_MANAGEMENT_PORT", "REDIS_PASSWORD", "REDIS_PORT",
        "BUSINESS_API_PORT", "COMPUTE_API_PORT"
    )
    $values = @{}
    foreach ($line in Get-Content -LiteralPath $envFile) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            $values[$Matches[1]] = $Matches[2].Trim()
        }
    }
    $missing = @($required | Where-Object { -not $values.ContainsKey($_) -or [string]::IsNullOrWhiteSpace($values[$_]) })
    if ($missing.Count -gt 0) {
        throw "Local configuration is missing values for: $($missing -join ', '). Edit .env using .env.example placeholders."
    }
    Write-Host "Configuration: .env values present ($envFile)"
}

function Read-State {
    if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) {
        return $null
    }
    try {
        return Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json
    }
    catch {
        throw "Runtime state is unreadable: $statePath. Remove only this state file after inspection."
    }
}

function Write-State($State) {
    Ensure-RuntimeDirectory
    $State | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statePath -Encoding utf8
}

function Remove-State {
    Remove-Item -LiteralPath $statePath -Force -ErrorAction SilentlyContinue
}

function Invoke-BoundedCommand {
    param(
        [Parameter(Mandatory)] [string] $FilePath,
        [Parameter(Mandatory)] [string[]] $ArgumentList,
        [Parameter(Mandatory)] [string] $Label,
        [Parameter(Mandatory)] [int] $Timeout,
        [hashtable] $Environment
    )

    $stdout = Get-LogPath "lifecycle-$($Label.ToLowerInvariant().Replace(' ', '-'))" "out"
    $stderr = Get-LogPath "lifecycle-$($Label.ToLowerInvariant().Replace(' ', '-'))" "err"
    Remove-Item -LiteralPath $stdout, $stderr -Force -ErrorAction SilentlyContinue
    $parameters = @{
        FilePath = $FilePath
        ArgumentList = $ArgumentList
        WorkingDirectory = $root
        RedirectStandardOutput = $stdout
        RedirectStandardError = $stderr
        PassThru = $true
        WindowStyle = "Hidden"
    }
    if ($Environment) { $parameters.Environment = $Environment }
    $process = Start-Process @parameters
    if (-not $process.WaitForExit($Timeout * 1000)) {
        & taskkill /PID $process.Id /T /F 2>$null | Out-Null
        $tail = if (Test-Path -LiteralPath $stderr) { (Get-Content -LiteralPath $stderr -Tail 25) -join "`n" } else { "" }
        throw "$Label timed out after $Timeout seconds. Error log: $stderr`n$tail"
    }
    if ($process.ExitCode -ne 0) {
        $tail = if (Test-Path -LiteralPath $stderr) { (Get-Content -LiteralPath $stderr -Tail 25) -join "`n" } else { "" }
        throw "$Label failed with exit code $($process.ExitCode). Error log: $stderr`n$tail"
    }
    return [pscustomobject]@{ stdout = $stdout; stderr = $stderr }
}

function Invoke-Compose([string[]] $Arguments, [string] $Label, [int] $CommandTimeout = $TimeoutSeconds) {
    $docker = (Get-Command docker -ErrorAction Stop).Source
    return Invoke-BoundedCommand -FilePath $docker -ArgumentList (@("compose") + $Arguments) -Label $Label -Timeout $CommandTimeout
}

function Start-TrackedService {
    param(
        [Parameter(Mandatory)] [string] $Name,
        [Parameter(Mandatory)] [string] $ScriptPath,
        [Parameter(Mandatory)] [string] $ActionName,
        [hashtable] $Environment,
        [Parameter(Mandatory)] [string] $Endpoint
    )

    $pwsh = Get-PwshPath
    $stdout = Get-LogPath $Name "out"
    $stderr = Get-LogPath $Name "err"
    Remove-Item -LiteralPath $stdout, $stderr -Force -ErrorAction SilentlyContinue
    $parameters = @{
        FilePath = $pwsh
        ArgumentList = @("-NoProfile", "-File", $ScriptPath, "-Action", $ActionName)
        WorkingDirectory = $root
        RedirectStandardOutput = $stdout
        RedirectStandardError = $stderr
        PassThru = $true
        WindowStyle = "Hidden"
    }
    if ($Environment) { $parameters.Environment = $Environment }
    $process = Start-Process @parameters
    return [pscustomobject]@{
        name = $Name
        pid = $process.Id
        startedAtUtc = $process.StartTime.ToUniversalTime().ToString("o")
        stdout = $stdout
        stderr = $stderr
        endpoint = $Endpoint
    }
}

function Stop-TrackedService($Service) {
    if (-not $Service) { return }
    try {
        $process = Get-Process -Id ([int]$Service.pid) -ErrorAction Stop
        $started = $process.StartTime.ToUniversalTime()
        $expected = [DateTime]::Parse($Service.startedAtUtc).ToUniversalTime()
        if ([Math]::Abs(($started - $expected).TotalSeconds) -gt 5) {
            Write-Warning "Skipped PID $($Service.pid): process identity changed"
            return
        }
        & taskkill /PID $process.Id /T /F 2>$null | Out-Null
        Write-Host "Stopped $($Service.name) (PID $($Service.pid))"
    }
    catch [System.Management.Automation.ItemNotFoundException] {
        Write-Host "$($Service.name) is already stopped"
    }
    catch {
        Write-Warning "Could not stop $($Service.name) (PID $($Service.pid)): $($_.Exception.Message)"
    }
}

function Stop-TrackedState($State) {
    if (-not $State) { return }
    foreach ($service in @($State.services)) {
        Stop-TrackedService $service
    }
}

function Get-LogTail($Service) {
    $parts = @()
    foreach ($path in @($Service.stdout, $Service.stderr)) {
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            $parts += "--- $path ---"
            $parts += Get-Content -LiteralPath $path -Tail 20
        }
    }
    return ($parts -join "`n")
}

function Test-Endpoint([string] $Endpoint) {
    try {
        $response = Invoke-WebRequest -Uri $Endpoint -TimeoutSec 5
        if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 300) {
            return "http:$($response.StatusCode)"
        }
        try {
            $body = $response.Content | ConvertFrom-Json
            if ($body.status -eq "UP" -or $body.status -eq "healthy") { return "healthy" }
            if ($null -ne $body.status) { return "responded:$($body.status)" }
        }
        catch { }
        return "healthy"
    }
    catch {
        return "unavailable"
    }
}

function Wait-Endpoint([string] $Name, [string] $Endpoint, [int] $Timeout, $Service) {
    $deadline = (Get-Date).AddSeconds($Timeout)
    do {
        if ($Service) {
            try {
                Get-Process -Id ([int]$Service.pid) -ErrorAction Stop | Out-Null
            }
            catch {
                throw "$Name exited before readiness at $Endpoint.`n$(Get-LogTail $Service)"
            }
        }
        $status = Test-Endpoint $Endpoint
        Write-Host "Readiness: $Name=$status"
        if ($status -eq "healthy") { return }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    $tail = if ($Service) { Get-LogTail $Service } else { "" }
    throw "$Name did not become ready at $Endpoint within $Timeout seconds.`n$tail"
}

function Wait-ComposeHealthy([int] $Timeout) {
    $services = @("postgres", "rabbitmq", "redis")
    $deadline = (Get-Date).AddSeconds($Timeout)
    $probeTimeout = [Math]::Min(15, $Timeout)
    do {
        $states = @{}
        foreach ($service in $services) {
            try {
                $query = Invoke-Compose -Arguments @("ps", "-q", $service) -Label "Inspect $service container" -CommandTimeout $probeTimeout
                $containerId = ((Get-Content -Raw -LiteralPath $query.stdout) -split "\s+")[0].Trim()
                if (-not $containerId) {
                    $states[$service] = "missing"
                    continue
                }
                $inspect = Invoke-BoundedCommand -FilePath ((Get-Command docker).Source) `
                    -ArgumentList @("inspect", "--format", "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}", $containerId) `
                    -Label "Inspect $service health" -Timeout $probeTimeout
                $states[$service] = (Get-Content -Raw -LiteralPath $inspect.stdout).Trim()
            }
            catch {
                $states[$service] = "probe-timeout"
            }
        }
        $summary = ($services | ForEach-Object { "$_=$($states[$_])" }) -join ", "
        Write-Host "Infrastructure readiness: $summary"
        if (@($states.Values | Where-Object { $_ -ne "healthy" }).Count -eq 0) {
            Write-Host "PASS: PostgreSQL, RabbitMQ, and Redis are healthy"
            return
        }
        if (@($states.Values | Where-Object { $_ -eq "unhealthy" }).Count -gt 0) {
            throw "Infrastructure reported unhealthy state: $summary"
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw "Infrastructure did not become healthy within $Timeout seconds"
}

function Invoke-Check {
    Assert-Tool "docker"
    Assert-Tool "python"
    Assert-Tool "java"
    Assert-Tool "npm"
    if (-not (Test-Path -LiteralPath (Join-Path $root ".env.example") -PathType Leaf)) {
        throw ".env.example is missing"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $root "compose.yaml") -PathType Leaf)) {
        throw "compose.yaml is missing"
    }
    Ensure-EnvironmentFile
    Invoke-Compose -Arguments @("config", "--quiet") -Label "Compose configuration validation"
    Write-Host "PASS: local lifecycle prerequisites and Compose configuration"
}

function Invoke-Status {
    $state = Read-State
    if ($state) {
        Write-Host "Tracked runtime state: $statePath"
        foreach ($service in @($state.services)) {
            $status = try { (Get-Process -Id ([int]$service.pid) -ErrorAction Stop).ProcessName } catch { "stopped" }
            Write-Host "$($service.name): PID $($service.pid) $status -> $($service.endpoint)"
        }
    }
    else {
        Write-Host "No tracked Java/Python/web processes"
    }
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        try {
            $result = Invoke-Compose -Arguments @("ps") -Label "Compose status"
            if (Test-Path -LiteralPath $result.stdout -PathType Leaf) {
                Get-Content -LiteralPath $result.stdout
            }
        }
        catch { Write-Warning $_.Exception.Message }
    }
}

function Invoke-Down {
    $state = Read-State
    Stop-TrackedState $state
    Remove-State
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        try {
            Invoke-Compose -Arguments @("down") -Label "Compose shutdown"
            Write-Host "Stopped RouteMind infrastructure; persistent development volumes were preserved"
        }
        catch {
            Write-Warning $_.Exception.Message
            throw
        }
    }
    else {
        Write-Warning "Docker is unavailable; tracked application processes were cleaned up"
    }
}

function Invoke-Up {
    $existing = Read-State
    if ($existing) {
        $live = @($existing.services | Where-Object {
                try { Get-Process -Id ([int]$_.pid) -ErrorAction Stop } catch { $null }
            })
        if ($live.Count -gt 0) {
            throw "RouteMind is already tracked as running. Use -Action status or -Action down first."
        }
        Remove-State
    }

    Invoke-Check
    $state = [pscustomobject]@{ schema = "routemind-local-runtime.v1"; startedAtUtc = [DateTime]::UtcNow.ToString("o"); phase = "starting"; services = @() }
    try {
        $state.phase = "infrastructure"
        Write-State $state
        Invoke-Compose -Arguments @("up", "-d", "--pull", "missing") -Label "Infrastructure startup"
        Wait-ComposeHealthy $TimeoutSeconds

        $state.phase = "application-services"
        Write-State $state
        $business = Start-TrackedService -Name "business-api" -ScriptPath (Join-Path $PSScriptRoot "business-api.ps1") `
            -ActionName "run" -Environment @{ ROUTEMIND_REDIS_PROJECTION_ENABLED = "true" } -Endpoint "$businessUri/actuator/health"
        $compute = Start-TrackedService -Name "compute-api" -ScriptPath (Join-Path $PSScriptRoot "compute-api.ps1") `
            -ActionName "run" -Endpoint "$computeUri/healthz"
        $state.services = @($business, $compute)
        Write-State $state

        $state.phase = "api-readiness"
        Write-State $state
        Wait-Endpoint "business-api" $business.endpoint $TimeoutSeconds $business
        Wait-Endpoint "compute-api" $compute.endpoint $TimeoutSeconds $compute

        if (-not $SkipWeb) {
            $state.phase = "web-startup"
            Write-State $state
            $web = Start-TrackedService -Name "web" -ScriptPath (Join-Path $PSScriptRoot "web-dev.ps1") `
                -ActionName "run" -Endpoint $webUri
            $state.services = @($business, $compute, $web)
            Write-State $state
            $state.phase = "web-readiness"
            Write-State $state
            Wait-Endpoint "web" $web.endpoint 60 $web
        }

        Write-Host "RouteMind local runtime is ready"
        Write-Host "Business API: $businessUri"
        Write-Host "Compute API:  $computeUri"
        if (-not $SkipWeb) { Write-Host "Web:          $webUri" }
        Write-Host "Stop safely with: ./scripts/dev-up.ps1 -Action down"
    }
    catch {
        Stop-TrackedState $state
        Remove-State
        throw
    }
}

Push-Location $root
try {
    switch ($Action) {
        "check" { Invoke-Check }
        "status" { Invoke-Status }
        "down" { Invoke-Down }
        "up" { Invoke-Up }
    }
}
finally {
    Pop-Location
}

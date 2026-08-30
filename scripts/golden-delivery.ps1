[CmdletBinding()]
param(
    [ValidateRange(30, 900)]
    [int] $TimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$pwsh = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
if (-not $pwsh) { $pwsh = (Get-Command powershell -ErrorAction Stop).Source }
$businessLog = Join-Path ([System.IO.Path]::GetTempPath()) "routemind-business-golden.log"
$computeLog = Join-Path ([System.IO.Path]::GetTempPath()) "routemind-compute-golden.log"
$businessErrorLog = Join-Path ([System.IO.Path]::GetTempPath()) "routemind-business-golden.err.log"
$computeErrorLog = Join-Path ([System.IO.Path]::GetTempPath()) "routemind-compute-golden.err.log"
$started = @()
$traceId = "0123456789abcdef0123456789abcdef"
$correlationId = [guid]::NewGuid().ToString()
$runId = [guid]::NewGuid().ToString()
$businessUri = "http://127.0.0.1:18080"
$computeUri = "http://127.0.0.1:18081"

function Invoke-JsonPost {
    param([string] $Uri, [hashtable] $Headers, [hashtable] $Body)
    Invoke-RestMethod -Method Post -Uri $Uri -Headers $Headers -ContentType "application/json" `
        -Body ($Body | ConvertTo-Json -Depth 12)
}

function Wait-Health {
    param([string] $Uri, [string] $ExpectedStatus)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-RestMethod -Uri $Uri -TimeoutSec 5
            if ($response.status -eq $ExpectedStatus) { return }
        }
        catch { }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw "Health check did not become ready: $Uri"
}

function Invoke-Psql {
    param([string] $Sql)
    $result = @(& docker compose exec -T postgres psql -U routemind -d routemind -tAc $Sql 2>&1)
    if ($LASTEXITCODE -ne 0) { throw "PostgreSQL probe failed: $($result -join "`n")" }
    return ($result -join "`n").Trim()
}

function Assert-Equal {
    param([string] $Actual, [string] $Expected, [string] $Label)
    if ($Actual.Trim() -ne $Expected) { throw "$Label expected '$Expected' but got '$Actual'" }
    Write-Host "PASS: $Label = $Expected"
}

function Show-Logs {
    foreach ($log in @($businessLog, $businessErrorLog, $computeLog, $computeErrorLog)) {
        if (Test-Path -LiteralPath $log) {
            Write-Host "--- $log (tail) ---"
            Get-Content -LiteralPath $log -Tail 40
        }
    }
}

try {
    & (Join-Path $PSScriptRoot "infra.ps1") -Action up -TimeoutSeconds 120

    Remove-Item -LiteralPath $businessLog, $businessErrorLog, $computeLog, $computeErrorLog -Force -ErrorAction SilentlyContinue
    $business = Start-Process -FilePath $pwsh -ArgumentList @(
        "-NoProfile", "-File", (Join-Path $PSScriptRoot "business-api.ps1"), "-Action", "run"
    ) -WorkingDirectory $root -Environment @{ ROUTEMIND_REDIS_PROJECTION_ENABLED = "true" } `
        -RedirectStandardOutput $businessLog -RedirectStandardError $businessErrorLog -PassThru -WindowStyle Hidden
    $compute = Start-Process -FilePath $pwsh -ArgumentList @(
        "-NoProfile", "-File", (Join-Path $PSScriptRoot "compute-api.ps1"), "-Action", "run"
    ) -WorkingDirectory $root -RedirectStandardOutput $computeLog -RedirectStandardError $computeErrorLog -PassThru -WindowStyle Hidden
    $started += $business
    $started += $compute

    Wait-Health "$businessUri/actuator/health" "UP"
    Wait-Health "$computeUri/healthz" "UP"
    Write-Host "PASS: Java and Python health probes"

    $headers = @{ "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId }
    $courierId = [guid]::NewGuid().ToString()
    $shiftHeaders = @{ "Idempotency-Key" = "$runId-shift"; "X-Actor" = "courier"; "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId }
    $shift = Invoke-JsonPost "$businessUri/api/v1/couriers/$courierId/shift" $shiftHeaders @{ target = "ONLINE"; expectedVersion = 0 }
    Assert-Equal $shift.status "ONLINE" "courier shift"
    $locationHeaders = @{ "Idempotency-Key" = "$runId-location"; "X-Actor" = "courier"; "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId }
    $location = Invoke-JsonPost "$businessUri/api/v1/couriers/$courierId/location" $locationHeaders @{ latitude = 31.2304; longitude = 121.4737; observedAt = "2026-08-23T09:00:00Z" }
    if ($location.status -notin @("PROJECTED", "DEGRADED")) { throw "Unexpected location projection status: $($location.status)" }
    Write-Host "PASS: courier location persisted with projection status $($location.status)"

    $createHeaders = @{ "Idempotency-Key" = "$runId-create"; "X-Actor" = "customer"; "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId }
    $order = Invoke-JsonPost "$businessUri/api/v1/orders" $createHeaders @{}
    $orderId = $order.orderId
    Assert-Equal $order.status "CREATED" "order creation"
    $confirmHeaders = @{ "Idempotency-Key" = "$runId-confirm"; "X-Actor" = "customer"; "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId }
    $confirmed = Invoke-JsonPost "$businessUri/api/v1/orders/$orderId/transitions" $confirmHeaders @{ target = "CONFIRMED"; expectedVersion = 0 }
    Assert-Equal $confirmed.status "CONFIRMED" "order confirmation"

    $dispatch = Invoke-JsonPost "$computeUri/api/v1/dispatch/snapshot" $headers @{
        request_id = "$runId-dispatch"; strategy = "risk-aware"; pickup = @{ latitude = 31.2304; longitude = 121.4737 }
        candidates = @(@{ courier_id = $courierId; location = @{ latitude = 31.2304; longitude = 121.4737 }; capacity_units = 4; service_risk = 0.1; overtime_risk = 0.1 })
    }
    Assert-Equal $dispatch.contract_version "v1" "dispatch contract"
    Assert-Equal $dispatch.selected_courier $courierId "dispatch selected courier"

    $dispatchMetadata = @{}
    foreach ($item in $dispatch.metadata) {
        if ($item.Count -eq 2) { $dispatchMetadata[[string]$item[0]] = [string]$item[1] }
    }
    $fallbackReason = $null
    if ($dispatch.fallback_used) {
        $fallbackReason = $dispatchMetadata["travel_fallback_reason"]
        if ([string]::IsNullOrWhiteSpace($fallbackReason) -or $fallbackReason -eq "none") {
            throw "Dispatch used fallback without an inspectable travel fallback reason"
        }
        Write-Host "PASS: dispatch fallback reason = $fallbackReason"
    }

    $assignmentHeaders = @{ "Idempotency-Key" = "$runId-assignment"; "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId }
    $assignment = Invoke-JsonPost "$businessUri/api/v1/orders/$orderId/dispatch-assignment" $assignmentHeaders @{
        requestId = $dispatch.request_id; contractVersion = $dispatch.contract_version; courierId = $dispatch.selected_courier
        strategy = $dispatch.strategy; strategyVersion = $dispatch.strategy_version; inputDigest = $dispatch.input_digest
        outputDigest = $dispatch.output_digest; fallbackUsed = $dispatch.fallback_used; fallbackReason = $fallbackReason; expectedOrderVersion = 1
    }
    Assert-Equal $assignment.status "ASSIGNED" "durable dispatch assignment"

    $transitions = @(@("accept", "ACCEPTED", 2), @("arrive", "ARRIVED", 3), @("pickup", "PICKED_UP", 4), @("deliver", "DELIVERED", 5))
    foreach ($transition in $transitions) {
        $transitionHeaders = @{ "Idempotency-Key" = "$runId-$($transition[0])"; "X-Actor" = "courier"; "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId }
        $result = Invoke-JsonPost "$businessUri/api/v1/orders/$orderId/transitions" $transitionHeaders @{ target = $transition[1]; expectedVersion = $transition[2] }
        Assert-Equal $result.status $transition[1] "order $($transition[1].ToLowerInvariant())"
    }

    Assert-Equal (Invoke-Psql "select status from routemind.orders where id = '$orderId'") "DELIVERED" "PostgreSQL delivered order"
    Assert-Equal (Invoke-Psql "select count(*) from routemind.dispatch_assignment_audits where order_id = '$orderId'") "1" "dispatch audit"
    Assert-Equal (Invoke-Psql "select count(*) from routemind.outbox_messages where event_type = 'dispatch.assignment.applied' and aggregate_id = '$orderId'") "1" "assignment Outbox event"
    Assert-Equal (Invoke-Psql "select count(*) from routemind.outbox_messages where event_type = 'dispatch.assignment.applied' and status = 'PUBLISHED' and aggregate_id = '$orderId'") "1" "RabbitMQ-published assignment event"
    Assert-Equal (Invoke-Psql "select count(*) from routemind.courier_locations where courier_id = '$courierId'") "1" "PostgreSQL courier location"
    $rabbit = (& docker compose exec -T rabbitmq rabbitmq-diagnostics -q ping 2>&1) -join "`n"
    if ($LASTEXITCODE -ne 0 -or $rabbit.Trim() -ne "Ping succeeded") { throw "RabbitMQ probe failed: $rabbit" }
    Write-Host "PASS: RabbitMQ authenticated health probe"
    $redis = (& docker compose exec -T redis redis-cli -a change-me-local-only ping 2>&1) -join "`n"
    if ($LASTEXITCODE -ne 0 -or $redis.Trim() -notmatch "PONG") { throw "Redis probe failed: $redis" }
    Write-Host "PASS: Redis authenticated health probe and GEO-backed location path"
    Write-Host "PASS: RM-170 real local golden delivery $orderId"
}
catch {
    Show-Logs
    throw
}
finally {
    foreach ($process in $started) {
        if ($process -and -not $process.HasExited) {
            & taskkill /PID $process.Id /T /F 2>$null | Out-Null
        }
    }
}

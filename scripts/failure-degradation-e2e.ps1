[CmdletBinding()]
param(
    [ValidateRange(60, 900)]
    [int] $TimeoutSeconds = 240
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$pwsh = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
if (-not $pwsh) { $pwsh = (Get-Command powershell -ErrorAction Stop).Source }
$python = (Get-Command python -ErrorAction Stop).Source
$businessUri = "http://127.0.0.1:18080"
$computeUri = "http://127.0.0.1:18081"
$traceId = "0123456789abcdef0123456789abcdef"
$runId = [guid]::NewGuid().ToString()
$correlationId = [guid]::NewGuid().ToString()
$started = [System.Collections.Generic.List[object]]::new()
$blackhole = $null
$businessLog = Join-Path ([System.IO.Path]::GetTempPath()) "routemind-business-failure.log"
$businessErrorLog = Join-Path ([System.IO.Path]::GetTempPath()) "routemind-business-failure.err.log"
$computeLog = Join-Path ([System.IO.Path]::GetTempPath()) "routemind-compute-failure.log"
$computeErrorLog = Join-Path ([System.IO.Path]::GetTempPath()) "routemind-compute-failure.err.log"

function Invoke-JsonPost {
    param([string] $Uri, [hashtable] $Headers, [hashtable] $Body)
    Invoke-RestMethod -Method Post -Uri $Uri -Headers $Headers -ContentType "application/json" `
        -Body ($Body | ConvertTo-Json -Depth 12) -TimeoutSec 10
}

function Invoke-JsonPostExpectStatus {
    param([string] $Uri, [hashtable] $Headers, [hashtable] $Body, [int] $Expected, [string] $Label)
    $actual = 0
    $responseBody = $null
    try {
        $response = Invoke-WebRequest -Method Post -Uri $Uri -Headers $Headers -ContentType "application/json" `
            -Body ($Body | ConvertTo-Json -Depth 12) -TimeoutSec 10
        $actual = [int]$response.StatusCode
        $responseBody = $response.Content
    }
    catch {
        if ($_.Exception.Response) {
            $actual = [int]$_.Exception.Response.StatusCode.value__
            $responseBody = "<http error response>"
        }
    }
    if ($actual -ne $Expected) { throw "$Label expected HTTP $Expected but got $actual ($responseBody)" }
    Write-Host "PASS: $Label = HTTP $Expected"
    return $null
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

function Assert-NotEqual {
    param([string] $Actual, [string] $Unexpected, [string] $Label)
    if ($Actual.Trim() -eq $Unexpected) { throw "$Label unexpectedly was '$Unexpected'" }
    Write-Host "PASS: $Label != $Unexpected"
}

function Wait-PsqlValue {
    param([string] $Sql, [string] $Expected, [string] $Label)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $actual = Invoke-Psql $Sql
        if ($actual -eq $Expected) {
            Write-Host "PASS: $Label = $Expected"
            return
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw "$Label expected '$Expected' but got '$actual'"
}

function Stop-Tree {
    param($Process)
    if ($Process -and -not $Process.HasExited) {
        & taskkill /PID $Process.Id /T /F 2>$null | Out-Null
    }
}

function Start-Business {
    $process = Start-Process -FilePath $pwsh -ArgumentList @(
        "-NoProfile", "-File", (Join-Path $PSScriptRoot "business-api.ps1"), "-Action", "run"
    ) -WorkingDirectory $root -Environment @{ ROUTEMIND_REDIS_PROJECTION_ENABLED = "true" } `
        -RedirectStandardOutput $businessLog -RedirectStandardError $businessErrorLog -PassThru -WindowStyle Hidden
    $started.Add($process)
    return $process
}

function Start-Compute {
    $process = Start-Process -FilePath $pwsh -ArgumentList @(
        "-NoProfile", "-File", (Join-Path $PSScriptRoot "compute-api.ps1"), "-Action", "run"
    ) -WorkingDirectory $root -RedirectStandardOutput $computeLog -RedirectStandardError $computeErrorLog -PassThru -WindowStyle Hidden
    $started.Add($process)
    return $process
}

function Assert-ComputeUnavailable {
    param([string] $Label)
    $available = $false
    try {
        Invoke-RestMethod -Uri "$computeUri/healthz" -TimeoutSec 3 | Out-Null
        $available = $true
    }
    catch { }
    if ($available) { throw "$Label expected compute health to be unavailable" }
    Write-Host "PASS: $Label"
}

function Assert-BusinessUnavailable {
    param([string] $Label)
    $available = $false
    try {
        Invoke-RestMethod -Uri "$businessUri/actuator/health" -TimeoutSec 3 | Out-Null
        $available = $true
    }
    catch { }
    if ($available) { throw "$Label expected business health to be unavailable" }
    Write-Host "PASS: $Label"
}

function Read-EventStreamItems {
    param([string] $After)
    $response = Invoke-WebRequest -Uri "$businessUri/api/v1/events/stream?after=$After" -TimeoutSec 10
    return @($response.Content -split "`r?`n" | Where-Object { $_ -match '^data:' } | ForEach-Object {
        ($_ -replace '^data:\s*', '') | ConvertFrom-Json
    })
}

function Assert-RequestTimeout {
    param([string] $Uri, [string] $Label)
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    $completed = $false
    try {
        Invoke-WebRequest -Method Post -Uri $Uri -ContentType "application/json" -Body '{}' -TimeoutSec 2 | Out-Null
        $completed = $true
    }
    catch { }
    finally { $watch.Stop() }
    if ($completed -or $watch.Elapsed.TotalSeconds -gt 8) {
        throw "$Label did not time out within the bounded deadline (elapsed $($watch.Elapsed.TotalSeconds) seconds)"
    }
    Write-Host "PASS: $Label (<$([math]::Ceiling($watch.Elapsed.TotalSeconds))s bounded timeout)"
}

function Show-Logs {
    foreach ($log in @($businessLog, $businessErrorLog, $computeLog, $computeErrorLog)) {
        if (Test-Path -LiteralPath $log) {
            Write-Host "--- $log (tail) ---"
            Get-Content -LiteralPath $log -Tail 50
        }
    }
}

try {
    & (Join-Path $PSScriptRoot "infra.ps1") -Action up -TimeoutSeconds 120
    Remove-Item -LiteralPath $businessLog, $businessErrorLog, $computeLog, $computeErrorLog -Force -ErrorAction SilentlyContinue
    $business = Start-Business
    $compute = Start-Compute
    Wait-Health "$businessUri/actuator/health" "UP"
    Wait-Health "$computeUri/healthz" "UP"
    Write-Host "PASS: Java and Python health probes"

    $commonHeaders = @{ "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId }

    # Redis projection loss keeps PostgreSQL durable and exposes DEGRADED.
    & docker compose stop redis | Out-Null
    $redisCourier = [guid]::NewGuid().ToString()
    $redisLocation = Invoke-JsonPost "$businessUri/api/v1/couriers/$redisCourier/location" `
        @{ "Idempotency-Key" = "$runId-redis-loss"; "X-Actor" = "courier"; "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId } `
        @{ latitude = 31.2304; longitude = 121.4737; sequence = 1; observedAt = "2026-08-23T09:10:00Z" }
    Assert-Equal $redisLocation.status "DEGRADED" "Redis loss location response"
    Assert-Equal (Invoke-Psql "select count(*) from routemind.courier_locations where courier_id = '$redisCourier'") "1" "Redis loss durable location"
    & docker compose up -d redis | Out-Null
    & (Join-Path $PSScriptRoot "infra.ps1") -Action up -TimeoutSeconds 120 | Out-Null
    $redisRecovered = Invoke-JsonPost "$businessUri/api/v1/couriers/$redisCourier/location" `
        @{ "Idempotency-Key" = "$runId-redis-recovered"; "X-Actor" = "courier"; "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId } `
        @{ latitude = 31.2305; longitude = 121.4738; sequence = 2; observedAt = "2026-08-23T09:11:00Z" }
    Assert-Equal $redisRecovered.status "PROJECTED" "Redis recovery location response"

    # Compute outage must not make Java durable creation look successful as dispatch.
    Stop-Tree $compute
    Assert-ComputeUnavailable "Compute outage health boundary"
    $outageCourier = [guid]::NewGuid().ToString()
    Assert-ComputeUnavailable "Compute outage dispatch boundary"
    $outageOrder = Invoke-JsonPost "$businessUri/api/v1/orders" `
        @{ "Idempotency-Key" = "$runId-compute-outage-order"; "X-Actor" = "customer"; "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId } @{}
    Assert-Equal $outageOrder.status "CREATED" "Java durable create during compute outage"
    $compute = Start-Compute
    Wait-Health "$computeUri/healthz" "UP"
    Write-Host "PASS: compute recovered"

    # Rabbit restart leaves the durable Outbox row pending/retryable, then recovers.
    & docker compose stop rabbitmq | Out-Null
    $rabbitOrder = Invoke-JsonPost "$businessUri/api/v1/orders" `
        @{ "Idempotency-Key" = "$runId-rabbit-restart-order"; "X-Actor" = "customer"; "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId } @{}
    Assert-Equal $rabbitOrder.status "CREATED" "Java create during RabbitMQ restart"
    Start-Sleep -Seconds 2
    Assert-NotEqual (Invoke-Psql "select status from routemind.outbox_messages where event_type = 'order.created' and aggregate_id = '$($rabbitOrder.orderId)'") "PUBLISHED" "Outbox state while RabbitMQ is down"
    & docker compose up -d rabbitmq | Out-Null
    & (Join-Path $PSScriptRoot "infra.ps1") -Action up -TimeoutSeconds 120 | Out-Null
    Wait-PsqlValue "select status from routemind.outbox_messages where event_type = 'order.created' and aggregate_id = '$($rabbitOrder.orderId)'" "PUBLISHED" "Outbox recovery after RabbitMQ restart"

    # Duplicate create is a durable idempotent replay, not a second event.
    $duplicateKey = "$runId-duplicate-order"
    $first = Invoke-JsonPost "$businessUri/api/v1/orders" `
        @{ "Idempotency-Key" = $duplicateKey; "X-Actor" = "customer"; "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId } @{}
    Assert-Equal $first.replayed.ToString().ToLowerInvariant() "false" "first duplicate command"
    $second = Invoke-JsonPost "$businessUri/api/v1/orders" `
        @{ "Idempotency-Key" = $duplicateKey; "X-Actor" = "customer"; "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId } @{}
    Assert-Equal $second.replayed.ToString().ToLowerInvariant() "true" "duplicate command replay"
    Assert-Equal $second.orderId $first.orderId "duplicate command order identity"
    Assert-Equal (Invoke-Psql "select count(*) from routemind.order_command_idempotency where idempotency_key = '$duplicateKey'") "1" "duplicate idempotency row"
    Assert-Equal (Invoke-Psql "select count(*) from routemind.outbox_messages where event_type = 'order.created' and aggregate_id = '$($first.orderId)'") "1" "duplicate event count"

    # Java restart preserves the authoritative snapshot and resumes SSE strictly after the durable cursor.
    $beforeRestart = @(Read-EventStreamItems "0")
    if ($beforeRestart.Count -eq 0) { throw "Event stream did not expose a durable cursor before restart" }
    $restartCursor = [string]$beforeRestart[-1].cursor
    Stop-Tree $business
    Assert-BusinessUnavailable "Business API restart boundary"
    $business = Start-Business
    Wait-Health "$businessUri/actuator/health" "UP"
    $snapshot = Invoke-RestMethod -Uri "$businessUri/api/v1/operations/snapshot" -TimeoutSec 10
    if (@($snapshot.orders.id) -notcontains $first.orderId) {
        throw "Authoritative operations snapshot lost order $($first.orderId) across restart"
    }
    Write-Host "PASS: authoritative operations snapshot recovered after Java restart"
    $recoveryOrder = Invoke-JsonPost "$businessUri/api/v1/orders" `
        @{ "Idempotency-Key" = "$runId-restart-order"; "X-Actor" = "customer"; "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId } @{}
    $afterRestart = @(Read-EventStreamItems $restartCursor)
    $recoveryEvents = @($afterRestart | Where-Object {
        $_.event.aggregateId -eq $recoveryOrder.orderId -and $_.event.eventType -eq "order.created"
    })
    Assert-Equal $recoveryEvents.Count.ToString() "1" "SSE resume event count after Java restart"

    # Offline courier is explicit in both the Java shift state and Python rationale.
    $offlineCourier = [guid]::NewGuid().ToString()
    $online = Invoke-JsonPost "$businessUri/api/v1/couriers/$offlineCourier/shift" `
        @{ "Idempotency-Key" = "$runId-offline-online"; "X-Actor" = "courier"; "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId } `
        @{ target = "ONLINE"; expectedVersion = 0 }
    Assert-Equal $online.status "ONLINE" "offline journey online transition"
    $offline = Invoke-JsonPost "$businessUri/api/v1/couriers/$offlineCourier/shift" `
        @{ "Idempotency-Key" = "$runId-offline-offline"; "X-Actor" = "courier"; "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId } `
        @{ target = "OFFLINE"; expectedVersion = 1 }
    Assert-Equal $offline.status "OFFLINE" "courier offline transition"
    $offlineDispatch = Invoke-JsonPost "$computeUri/api/v1/dispatch/snapshot" $commonHeaders @{
        request_id = "$runId-offline-dispatch"; strategy = "risk-aware"; pickup = @{ latitude = 31.2304; longitude = 121.4737 }
        candidates = @(@{ courier_id = $offlineCourier; location = @{ latitude = 31.2304; longitude = 121.4737 }; capacity_units = 4; state = "offline" })
    }
    if ($null -ne $offlineDispatch.selected_courier) { throw "offline courier was selected" }
    if (($offlineDispatch.rationale -join " ") -notmatch "courier_state=offline") { throw "offline rejection reason missing" }
    Write-Host "PASS: offline courier rejected with explicit rationale"
    Invoke-JsonPostExpectStatus "$businessUri/api/v1/couriers/$offlineCourier/shift" `
        @{ "Idempotency-Key" = "$runId-offline-stale"; "X-Actor" = "courier"; "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId } `
        @{ target = "ONLINE"; expectedVersion = 1 } 409 "stale offline shift command" | Out-Null

    # A local listener that accepts but does not answer proves the caller timeout is bounded.
    Stop-Tree $compute
    $blackholeCode = 'import socket,time; s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); s.bind(("127.0.0.1",18081)); s.listen(1); c,_=s.accept(); time.sleep(20)'
    $blackhole = Start-Process -FilePath $python -ArgumentList @("-c", $blackholeCode) -PassThru -WindowStyle Hidden
    $started.Add($blackhole)
    Start-Sleep -Seconds 1
    Assert-RequestTimeout "$computeUri/api/v1/dispatch/snapshot" "bounded dispatch timeout"
    $timeoutOrder = Invoke-JsonPost "$businessUri/api/v1/orders" `
        @{ "Idempotency-Key" = "$runId-dispatch-timeout-order"; "X-Actor" = "customer"; "X-Trace-Id" = $traceId; "X-Correlation-Id" = $correlationId } @{}
    Assert-Equal $timeoutOrder.status "CREATED" "Java durable create during dispatch timeout"
    Stop-Tree $blackhole
    $blackhole = $null
    $compute = Start-Compute
    Wait-Health "$computeUri/healthz" "UP"
    Write-Host "PASS: RM-171 failure and degradation E2E $runId"
}
catch {
    Show-Logs
    throw
}
finally {
    if ($blackhole) { Stop-Tree $blackhole }
    & docker compose up -d redis rabbitmq | Out-Null
    foreach ($process in $started) { Stop-Tree $process }
}

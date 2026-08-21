[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Push-Location $root
try {
    Write-Host "ROUTEMIND AUTOPILOT"
    Write-Host ""
    Write-Host "Git:"
    git status --short --branch
    $commitCount = [int](git rev-list --count --all)
    if ($commitCount -gt 0) {
        git log --oneline --decorate -5
    }
    else {
        Write-Host "No commits yet"
    }

    $graph = Get-Content -Raw -LiteralPath "TASK_GRAPH.yaml" | ConvertFrom-Json
    $current = @($graph.tasks | Where-Object { $_.status -in @("in_progress", "validating", "implemented") })
    $passed = @($graph.tasks | Where-Object { $_.status -eq "passed" })
    $passedIds = @($passed | ForEach-Object { $_.id })
    $eligible = @($graph.tasks | Where-Object {
        $_.status -in @("pending", "ready") -and
        @($_.depends_on | Where-Object { $_ -notin $passedIds }).Count -eq 0
    })

    Write-Host ""
    Write-Host "Phase: $((Get-Content PROGRESS.md | Select-String '^Current Phase:').Line -replace '^Current Phase:\s*', '')"
    Write-Host "Current: $(if ($current) { ($current | ForEach-Object { "$($_.id) $($_.title) [$($_.status)]" }) -join '; ' } else { 'NONE' })"
    Write-Host "Passed: $($passed.Count) / $($graph.tasks.Count)"
    Write-Host "Next eligible: $(if ($eligible) { ($eligible | ForEach-Object { $_.id }) -join ', ' } else { 'NONE' })"
    Write-Host "Human action: NONE recorded"
    Write-Host ""

    & (Join-Path $PSScriptRoot "verify.ps1")
}
finally {
    Pop-Location
}

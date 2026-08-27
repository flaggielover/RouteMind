[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$apiKey = [Environment]::GetEnvironmentVariable("VULTR_API_KEY", "Process")
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    $apiKey = [Environment]::GetEnvironmentVariable("VULTR_API_KEY", "User")
}
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    throw "VULTR_API_KEY is MISSING"
}

$headers = @{ Authorization = "Bearer $apiKey" }

function Invoke-VultrGet([string]$Path) {
    return Invoke-RestMethod -Method Get -Uri "https://api.vultr.com/v2$Path" -Headers $headers -TimeoutSec 30
}

try {
    $vpcs = @((Invoke-VultrGet "/vpcs?per_page=500").vpcs | Where-Object { $_.region -eq "nrt" })
    $relatedEndpoints = [ordered]@{
        instances = "/instances?per_page=500"
        kubernetesClusters = "/kubernetes/clusters?per_page=500"
        loadBalancers = "/load-balancers?per_page=500"
        bareMetal = "/bare-metals?per_page=500"
        managedDatabases = "/databases?per_page=500"
    }
    $related = [ordered]@{}
    $complete = $true
    foreach ($entry in $relatedEndpoints.GetEnumerator()) {
        try {
            $response = Invoke-VultrGet $entry.Value
            $collection = @(
                $response.PSObject.Properties |
                    Where-Object { $_.Name -ne "meta" } |
                    Select-Object -First 1 -ExpandProperty Value
            )
            $related[$entry.Key] = [ordered]@{
                status = "READ_OK"
                accountCount = $collection.Count
                nrtCount = @($collection | Where-Object { $_.region -eq "nrt" }).Count
            }
        }
        catch {
            $complete = $false
            $related[$entry.Key] = [ordered]@{
                status = "READ_UNAVAILABLE"
                accountCount = $null
                nrtCount = $null
            }
        }
    }

    $audit = @(
        $vpcs | ForEach-Object {
            [ordered]@{
                id = [string]$_.id
                region = [string]$_.region
                dateCreated = ([DateTime]$_.date_created).ToUniversalTime().ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
                description = [string]$_.description
                cidr = "$($_.v4_subnet)/$($_.v4_subnet_mask)"
                internet = [bool]$_.internet
                ownership = "UNKNOWN"
                apparentlyUnused = "UNKNOWN"
                safeReuse = "NOT_SAFE_TO_REUSE"
            }
        }
    )
    [ordered]@{
        schema = "routemind-r4-vpc-quota-audit.v1"
        observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        provider = "Vultr"
        region = "nrt"
        mutationPerformed = $false
        nrtVpcCount = $audit.Count
        nrtVpcs = $audit
        relatedResourceInventory = $related
        conclusion = if ($complete) { "NO_EXISTING_VPC_SAFE_REUSE_PROVEN" } else { "AUDIT_INCOMPLETE" }
    } | ConvertTo-Json -Depth 8
}
finally {
    $apiKey = $null
    $headers = $null
}

$ErrorActionPreference = "Stop"

param(
  [string]$Upstream,
  [string]$ApiKey,
  [int]$Port = 8000
)

$RootDir = Split-Path -Parent $PSScriptRoot
$VenvDir = Join-Path $RootDir ".venv"

if (-not (Test-Path $VenvDir)) {
  & "$RootDir\scripts\setup.ps1"
}

if (-not $Upstream) {
  $Upstream = Read-Host "Enter upstream base URL"
}

if (-not $Upstream) {
  Write-Error "Upstream URL is required."
}

$Upstream = $Upstream.TrimEnd("/")
$UpstreamHasV1 = $false
if ($Upstream.EndsWith("/v1")) {
  $UpstreamHasV1 = $true
}

$allowedGet = @(200,201,204,301,302,303,307,308,401,403,405,429)
$allowedPost = @(200,201,204,301,302,303,307,308,400,401,403,405,415,422,429)

function Test-Endpoint {
  param(
    [string]$Url,
    [string]$Method = "Get",
    [int[]]$Allowed = $allowedGet
  )

  $headers = @{}
  if ($ApiKey) {
    $headers["Authorization"] = "Bearer $ApiKey"
  }

  try {
    if ($Method -eq "Post") {
      $response = Invoke-WebRequest -Uri $Url -Method $Method -Headers $headers -Body "{}" `
        -ContentType "application/json" -TimeoutSec 10
    } else {
      $response = Invoke-WebRequest -Uri $Url -Method $Method -Headers $headers -TimeoutSec 10
    }
    $status = [int]$response.StatusCode
  } catch {
    if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
      $status = [int]$_.Exception.Response.StatusCode.value__
    } else {
      Write-Error "FAIL: $Url (no response)"
      return $false
    }
  }

  if ($Allowed -contains $status) {
    Write-Output "OK: $Url ($status)"
    return $true
  }

  Write-Error "FAIL: $Url ($status)"
  return $false
}

Write-Output "Validating upstream..."
if (-not (Test-Endpoint "$Upstream" -Method Get -Allowed $allowedGet)) { exit 1 }
if (-not (Test-Endpoint "$Upstream/responses" -Method Post -Allowed $allowedPost)) { exit 1 }
if (-not $UpstreamHasV1) {
  if (-not (Test-Endpoint "$Upstream/v1/responses" -Method Post -Allowed $allowedPost)) { exit 1 }
}

$env:UPSTREAM_BASE_URL = $Upstream
if ($ApiKey) {
  $env:UPSTREAM_API_KEY = $ApiKey
}

& "$VenvDir\Scripts\python.exe" -m uvicorn src.main:app --host 0.0.0.0 --port $Port

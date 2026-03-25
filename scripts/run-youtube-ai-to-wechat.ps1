param(
  [string]$Topic = "",
  [string[]]$Keywords = @(),
  [string]$TimeRange = "7d",
  [string[]]$Language = @("zh", "en"),
  [string]$ArticleType = "auto",
  [int]$MaxCandidates = 20,
  [int]$MaxSelectedVideos = 3,
  [int]$PerQuery = 8,
  [string]$FixturesDir = "",
  [string]$RunName = "",
  [string]$ResumeFrom = "",
  [switch]$Preview,
  [switch]$Publish,
  [switch]$RenderOnly,
  [switch]$DiscoveryOnly,
  [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"

if (-not $Topic -and -not $RunName) {
  throw "Provide -Topic for a new run, or pass -RunName for an existing run."
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$skillRoot = Resolve-Path (Join-Path $scriptDir "..")
$runnerPath = Join-Path $skillRoot "assets\examples\environments\run_oneit_topic.ps1"

if (-not (Test-Path $runnerPath)) {
  throw "Local runner not found: $runnerPath"
}

if (-not $Preview -and -not $Publish -and -not $RenderOnly -and -not $DiscoveryOnly) {
  $Preview = $true
}

$invokeParams = @{}
if ($Topic) {
  $invokeParams.Topic = $Topic
}
if ($Keywords -and $Keywords.Count -gt 0) {
  $invokeParams.Keywords = $Keywords
}
$invokeParams.TimeRange = $TimeRange
$invokeParams.Language = $Language
$invokeParams.ArticleType = $ArticleType
$invokeParams.MaxCandidates = $MaxCandidates
$invokeParams.MaxSelectedVideos = $MaxSelectedVideos
$invokeParams.PerQuery = $PerQuery
if ($FixturesDir) {
  $invokeParams.FixturesDir = $FixturesDir
}
if ($RunName) {
  $invokeParams.RunName = $RunName
}
if ($ResumeFrom) {
  $invokeParams.ResumeFrom = $ResumeFrom
}
if ($Preview) {
  $invokeParams.Preview = $true
}
if ($Publish) {
  $invokeParams.Publish = $true
}
if ($RenderOnly) {
  $invokeParams.RenderOnly = $true
}
if ($DiscoveryOnly) {
  $invokeParams.DiscoveryOnly = $true
}

if ($PrintOnly) {
  Write-Host "Runner:"
  Write-Host $runnerPath
  Write-Host ""
  Write-Host "Parameters:"
  $invokeParams.GetEnumerator() | Sort-Object Name | ForEach-Object {
    $value = $_.Value
    if ($value -is [System.Array]) {
      $rendered = ($value -join ", ")
    } else {
      $rendered = [string]$value
    }
    Write-Host ("- {0}: {1}" -f $_.Name, $rendered)
  }
  exit 0
}

Push-Location $skillRoot
try {
  & $runnerPath @invokeParams
  exit $LASTEXITCODE
} finally {
  Pop-Location
}

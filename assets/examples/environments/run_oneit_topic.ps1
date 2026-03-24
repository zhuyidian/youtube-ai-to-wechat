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
  [switch]$DiscoveryOnly
)

$ErrorActionPreference = "Stop"

function New-TopicSlug {
  param([string]$Value)
  $lower = $Value.ToLowerInvariant()
  $slug = [Regex]::Replace($lower, "[^a-z0-9]+", "-").Trim("-")
  if (-not $slug) {
    return "topic"
  }
  if ($slug.Length -gt 32) {
    return $slug.Substring(0, 32).Trim("-")
  }
  return $slug
}

function Invoke-CheckedCommand {
  param([string[]]$Command)
  Write-Host ($Command -join " ")
  & $Command[0] $Command[1..($Command.Count - 1)]
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$envDir = Resolve-Path $scriptDir
$skillRoot = Resolve-Path (Join-Path $scriptDir "..\..\..")
Set-Location $skillRoot

if (-not $RunName) {
  if (-not $Topic) {
    throw "Provide -Topic for a new run, or pass -RunName for an existing run."
  }

  $mode = if ($Publish) { "publish" } elseif ($Preview) { "preview" } else { "full" }
  $RunName = "$(Get-Date -Format 'yyyy-MM-dd')-$(New-TopicSlug $Topic)-$mode"
}

$runDir = ".\.runs\$RunName"
$taskPath = Join-Path $runDir "topic_input.auto.json"
$searchPath = Join-Path $runDir "search_candidates.auto.json"
$rankedPath = Join-Path $runDir "ranked_candidates.auto.json"
$transcriptPath = Join-Path $runDir "transcript_pack.auto.json"
$sourcePackPath = Join-Path $runDir "source_pack.auto.json"
$runScript = Join-Path $envDir "run_oneit.ps1"

New-Item -ItemType Directory -Force $runDir | Out-Null

if ($Topic) {
  if (-not $Keywords -or $Keywords.Count -eq 0) {
    $Keywords = @($Topic)
  }

  $task = [ordered]@{
    topic = $Topic
    keywords = @($Keywords)
    time_range = $TimeRange
    language = @($Language)
    article_type = $ArticleType
    publish_mode = "draft_only"
    max_candidates = $MaxCandidates
    max_selected_videos = $MaxSelectedVideos
  }

  $task | ConvertTo-Json -Depth 6 | Set-Content -Path $taskPath -Encoding UTF8

  if (-not $FixturesDir) {
    Write-Warning "No -FixturesDir was provided. The current transcript stage falls back to metadata-only output unless you have a separate caption source wired in."
  }

  $searchCmd = @(
    "python", ".\scripts\search_youtube.py",
    $taskPath,
    "--output", $searchPath,
    "--per-query", "$PerQuery"
  )
  if ($FixturesDir) {
    $searchCmd += @("--fixtures-dir", $FixturesDir)
  }

  $rankCmd = @(
    "python", ".\scripts\rank_candidates.py",
    $searchPath,
    "--output", $rankedPath
  )

  $transcriptCmd = @(
    "python", ".\scripts\fetch_transcript.py",
    $rankedPath,
    "--output", $transcriptPath
  )
  if ($FixturesDir) {
    $transcriptCmd += @("--fixtures-dir", $FixturesDir)
  }

  $researchCmd = @(
    "python", ".\scripts\collect_research.py",
    $transcriptPath,
    "--output", $sourcePackPath
  )
  if ($FixturesDir) {
    $researchCmd += @("--fixtures-dir", $FixturesDir)
  }

  Write-Host "Mode         : topic-driven"
  Write-Host "Run dir      : $runDir"
  Write-Host "Topic        : $Topic"
  Write-Host "Source pack  : $sourcePackPath"
  if ($FixturesDir) {
    Write-Host "Fixtures     : $FixturesDir"
  }
  Write-Host ""

  Invoke-CheckedCommand $searchCmd
  Invoke-CheckedCommand $rankCmd
  Invoke-CheckedCommand $transcriptCmd
  Invoke-CheckedCommand $researchCmd
} elseif (-not (Test-Path $sourcePackPath)) {
  throw "No source pack found at $sourcePackPath. Provide -Topic for a new run or restore the existing run artifacts."
}

if ($DiscoveryOnly) {
  Write-Host ""
  Write-Host "Discovery-only mode complete."
  Write-Host "Source pack  : $sourcePackPath"
  exit 0
}

$params = @{
  SourcePack = $sourcePackPath
  RunName = $RunName
}
if ($ResumeFrom) {
  $params.ResumeFrom = $ResumeFrom
}
if ($Preview) {
  $params.Preview = $true
}
if ($Publish) {
  $params.Publish = $true
}
if ($RenderOnly) {
  $params.RenderOnly = $true
}

& $runScript @params
exit $LASTEXITCODE


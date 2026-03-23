param(
  [string]$SourcePack = "",
  [string]$RunName = "",
  [string]$ResumeFrom = "",
  [switch]$Preview,
  [switch]$Publish,
  [switch]$RenderOnly
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$envDir = Resolve-Path $scriptDir
$skillRoot = Resolve-Path (Join-Path $scriptDir "..\..\..")
Set-Location $skillRoot

if (-not $SourcePack) {
  $SourcePack = ".\.runs\example\source_pack_v2.json"
}

if (-not $RunName) {
  if ($Publish) {
    $RunName = "$(Get-Date -Format 'yyyy-MM-dd')-oneit-publish"
  } elseif ($Preview) {
    $RunName = "$(Get-Date -Format 'yyyy-MM-dd')-oneit-preview"
  } else {
    $RunName = "$(Get-Date -Format 'yyyy-MM-dd')-oneit-full"
  }
}

$runDir = ".\.runs\$RunName"
$runScript = Join-Path $envDir "run_live_pipeline.prod.oneit.ps1"
$previewScript = Join-Path $envDir "render_article_preview.oneit.ps1"

if ($RenderOnly) {
  & $previewScript -RunDir $runDir
  exit $LASTEXITCODE
}

Write-Host "Mode         : " -NoNewline
if ($Publish) {
  Write-Host "publish"
} elseif ($Preview) {
  Write-Host "preview"
} else {
  Write-Host "full"
}
Write-Host "Run dir      : $runDir"
Write-Host "Source pack  : $SourcePack"
if ($ResumeFrom) {
  Write-Host "Resume from  : $ResumeFrom"
}
Write-Host ""

$params = @{
  SourcePack = $SourcePack
  RunName = $RunName
}
if ($ResumeFrom) {
  $params.ResumeFrom = $ResumeFrom
}
if ($Publish) {
  $params.Publish = $true
}

& $runScript @params
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

if ($Preview -or -not $Publish) {
  Write-Host ""
  Write-Host "Refreshing markdown preview..."
  & $previewScript -RunDir $runDir
  exit $LASTEXITCODE
}

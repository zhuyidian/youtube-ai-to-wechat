param(
  [string]$SourcePack = "",
  [string]$RunName = "",
  [string]$ResumeFrom = "",
  [switch]$Publish
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$skillRoot = Resolve-Path (Join-Path $scriptDir "..\..\..")
Set-Location $skillRoot

$localEnvScript = Join-Path $scriptDir "set_minimax_env.local.ps1"
if (Test-Path $localEnvScript) {
  . $localEnvScript
}

if (-not $SourcePack) {
  $SourcePack = ".\.runs\example\source_pack_v2.json"
}

if (-not $RunName) {
  $RunName = "$(Get-Date -Format 'yyyy-MM-dd')-oneit-prod"
}

$outputDir = ".\.runs\$RunName"
$configPath = ".\assets\examples\environments\live_config.prod.example.json"
$logPath = Join-Path $outputDir "run.log"
$stdoutPath = Join-Path $outputDir "run.stdout.log"
$stderrPath = Join-Path $outputDir "run.stderr.log"

$requiredVars = @("MINIMAX_API_KEY")
if ($Publish) {
  $requiredVars += "WECHAT_ACCESS_TOKEN"
}

$missingVars = @(
  $requiredVars | Where-Object { -not [Environment]::GetEnvironmentVariable($_) }
)
if ($missingVars.Count -gt 0) {
  throw "Missing env vars: $($missingVars -join ', ')"
}

New-Item -ItemType Directory -Force $outputDir | Out-Null

$argumentList = @(
  ".\scripts\run_live_pipeline.py",
  $SourcePack,
  "--output-dir", $outputDir,
  "--live-config", $configPath,
  "--execute-llm",
  "--execute-images",
  "--max-retries", "1",
  "--retry-delay-seconds", "3",
  "--retry-policy", "smart"
)
if ($ResumeFrom) {
  $argumentList += @("--resume-from", $ResumeFrom)
}
if ($Publish) {
  $argumentList += "--execute-publish"
}

Write-Host "Skill root   : $skillRoot"
Write-Host "Source pack  : $SourcePack"
Write-Host "Output dir   : $outputDir"
Write-Host "Config       : $configPath"
Write-Host "Publish      : $Publish"
if ($ResumeFrom) {
  Write-Host "Resume from  : $ResumeFrom"
}
Write-Host "Log          : $logPath"
Write-Host ""
Write-Host "Running command:"
Write-Host ((@('python') + $argumentList) -join ' ')
Write-Host ""

if (Test-Path $stdoutPath) { Remove-Item $stdoutPath -Force }
if (Test-Path $stderrPath) { Remove-Item $stderrPath -Force }

$process = Start-Process -FilePath "python" -ArgumentList $argumentList -WorkingDirectory $skillRoot -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -Wait -PassThru -NoNewWindow

$stdout = if (Test-Path $stdoutPath) { Get-Content -Raw $stdoutPath } else { "" }
$stderr = if (Test-Path $stderrPath) { Get-Content -Raw $stderrPath } else { "" }
$combined = @()
if ($stdout) { $combined += $stdout.TrimEnd() }
if ($stderr) { $combined += $stderr.TrimEnd() }
$combinedText = ($combined -join [Environment]::NewLine)
Set-Content -Encoding utf8 $logPath $combinedText
if ($stdout) { Write-Host $stdout.TrimEnd() }
if ($stderr) { Write-Host $stderr.TrimEnd() }

if ($process.ExitCode -ne 0) {
  exit $process.ExitCode
}

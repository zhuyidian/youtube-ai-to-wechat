param(
  [string]$RunName = "",
  [string]$RunDir = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$workspaceRoot = Resolve-Path (Join-Path $scriptDir "..\..\..\..\..\..")

if (-not $RunDir) {
  if (-not $RunName) {
    $RunName = "$(Get-Date -Format 'yyyy-MM-dd')-oneit-prod"
  }
  $RunDir = ".\.runs\$RunName"
}

if ([System.IO.Path]::IsPathRooted($RunDir)) {
  $resolvedRunDir = $RunDir
} else {
  $resolvedRunDir = Join-Path $workspaceRoot $RunDir
}

$finalPackage = Join-Path $resolvedRunDir "final_article_package_live.json"
$previewPath = Join-Path $resolvedRunDir "article_preview.md"
$previewHtmlPath = Join-Path $resolvedRunDir "article_preview.html"

if (-not (Test-Path $finalPackage)) {
  throw "Missing final article package: $finalPackage"
}

$pyPath = Join-Path $env:TEMP "render_article_preview_oneit.py"
$pyContent = @"
import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
final = json.loads((run_dir / 'final_article_package_live.json').read_text(encoding='utf-8-sig'))
body = (final.get('body_markdown') or '').strip()
if not body:
    raise SystemExit('final_article_package_live.json is missing body_markdown')
out_path = run_dir / 'article_preview.md'
out_path.write_text(body + '\n', encoding='utf-8')
html = (final.get('final_html') or final.get('body_html') or '').strip()
if not html:
    raise SystemExit('final_article_package_live.json is missing final_html/body_html')
html_path = run_dir / 'article_preview.html'
html_path.write_text(html + '\n', encoding='utf-8')
print(out_path)
print(html_path)
"@

Set-Content $pyPath -Value $pyContent -Encoding utf8
python $pyPath $resolvedRunDir

Write-Host "Run dir      : $resolvedRunDir"
Write-Host "Preview file : $previewPath"
Write-Host "Preview html : $previewHtmlPath"

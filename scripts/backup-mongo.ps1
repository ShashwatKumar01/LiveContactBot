# Export ContactBot MongoDB to ./backups/
# Usage:
#   $env:MONGODB_URI = "mongodb://..."
#   $env:MONGODB_DATABASE = "contactbot"   # optional, default contactbot
#   .\scripts\backup-mongo.ps1

$ErrorActionPreference = "Stop"

$uri = $env:MONGODB_URI
if (-not $uri) {
    Write-Error "Set MONGODB_URI (e.g. from Railway MongoDB service variables)."
}

$db = if ($env:MONGODB_DATABASE) { $env:MONGODB_DATABASE } else { "ChatReplyBot" }
$stamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$root = Join-Path $PSScriptRoot ".." "backups"
$out = Join-Path $root "contactbot_$stamp"

if (-not (Get-Command mongodump -ErrorAction SilentlyContinue)) {
    Write-Error "mongodump not found. Install MongoDB Database Tools: https://www.mongodb.com/try/download/database-tools"
}

New-Item -ItemType Directory -Force -Path $root | Out-Null
Write-Host "Dumping database '$db' to $out ..."
mongodump --uri="$uri" --db=$db --out=$out

$zip = "$out.zip"
Compress-Archive -Path $out -DestinationPath $zip -Force
Write-Host "Done. Folder: $out"
Write-Host "Archive:  $zip"

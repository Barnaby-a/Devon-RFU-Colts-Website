# Copy all files from static/sponsors to static/team-logos
# Run this in PowerShell from the project root (Task 2)

$src = Join-Path $PSScriptRoot '..\static\sponsors\*'
$dst = Join-Path $PSScriptRoot '..\static\team-logos\'

# Ensure destination exists
New-Item -ItemType Directory -Force -Path $dst | Out-Null

# Copy files
Copy-Item -Path $src -Destination $dst -Force -Recurse

Write-Host "Copied files from static/sponsors to static/team-logos" -ForegroundColor Green

param([switch]$SkipGitleaks)
$ErrorActionPreference = "Stop"
python -m ruff check .
python -m pytest
npm --prefix .\frontend ci
npm --prefix .\frontend run build
& .\scripts\audit-public-release.ps1 -SkipGitleaks:$SkipGitleaks
python .\scripts\scan-public-assets.py
git diff --check
Write-Host "Public release verification passed." -ForegroundColor Green


$ErrorActionPreference = "Stop"

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Push-Location $repo
try {
    python -m ruff check .
    python -m pytest
    npm --prefix .\frontend ci
    npm --prefix .\frontend run build
    git diff --check
    & .\scripts\audit-public-release.ps1 -SkipGitleaks
    python .\scripts\scan-public-assets.py

    $trackedOut = git ls-files frontend/out
    if ($trackedOut) {
        throw "frontend/out is still tracked. Remove it before release."
    }

    if (-not (Test-Path .\frontend\features\shared\workspace-query.ts)) {
        throw "The shared workspace data layer is missing."
    }

    Write-Host "GroundsOps final release checks passed." -ForegroundColor Green
}
finally {
    Pop-Location
}

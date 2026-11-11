param([switch]$SkipGitleaks)
$ErrorActionPreference = "Stop"

$blocked = git ls-files | Where-Object {
    $_ -match '(^|/)(\.env($|\.)|playwright-report|test-results|backups?|dumps?|release-audit)(/|$)' -or
    $_ -match '\.(log|dump|sql|sqlite|db|pem|key|p12|pfx|sarif)$'
}
if ($blocked) { throw "Unsafe tracked files:`n$($blocked -join "`n")" }

$markers = @('AKIA[0-9A-Z]{16}','rep_[A-Za-z0-9]{20,}','-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----','aws_secret_access_key\s*=\s*[^r]')
foreach ($marker in $markers) {
    & git grep -I -n -E -e $marker -- . ':!*.example' ':!docs/*' ':!scripts/audit-public-release.ps1' | Out-Null
    $grepExit = $LASTEXITCODE
    if ($grepExit -eq 0) { throw "Potential credential found in tracked files. Pattern: $marker" }
    if ($grepExit -gt 1) { throw "git grep failed while checking pattern: $marker" }
}

if (-not $SkipGitleaks) {
    if (Get-Command gitleaks -ErrorAction SilentlyContinue) {
        gitleaks git --redact --config .gitleaks.toml --exit-code 1
    } else {
        throw "Install Gitleaks or rerun with -SkipGitleaks only when CI will perform the full-history scan."
    }
}

Write-Host "Public repository audit passed." -ForegroundColor Green
exit 0


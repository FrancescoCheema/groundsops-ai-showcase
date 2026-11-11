param(
    [string]$Repository = "FrancescoCheema/GroundsOps-AI",
    [Parameter(Mandatory = $true)][string]$DemoUrl,
    [switch]$MakePublic,
    [switch]$CreateV1Release
)
$ErrorActionPreference = "Stop"
gh auth status

gh repo edit $Repository --homepage $DemoUrl --add-topic fastapi --add-topic nextjs --add-topic postgresql --add-topic docker --add-topic github-actions --add-topic ai --add-topic landscaping --add-topic saas

if ($MakePublic) {
    $answer = Read-Host "Type PUBLIC to make $Repository publicly visible"
    if ($answer -ne "PUBLIC") { throw "Public visibility confirmation was not provided." }
    gh repo edit $Repository --visibility public --accept-visibility-change-consequences
}

$protection = @{
    required_status_checks = @{
        strict = $true
        contexts = @("backend", "frontend", "e2e", "secrets", "public-audit", "backup-restore", "load-smoke")
    }
    enforce_admins = $false
    required_pull_request_reviews = @{
        dismiss_stale_reviews = $true
        require_code_owner_reviews = $false
        required_approving_review_count = 1
        require_last_push_approval = $false
    }
    restrictions = $null
    required_conversation_resolution = $true
    allow_force_pushes = $false
    allow_deletions = $false
} | ConvertTo-Json -Depth 8
$protection | gh api --method PUT "repos/$Repository/branches/main/protection" --input -

if ($CreateV1Release) {
    git fetch origin
    if ((git status --porcelain)) { throw "Working tree must be clean before release." }
    $mainSha = (git rev-parse origin/main).Trim()
    git tag -a v1.0.0 $mainSha -m "GroundsOps AI v1.0.0"
    git push origin v1.0.0
}


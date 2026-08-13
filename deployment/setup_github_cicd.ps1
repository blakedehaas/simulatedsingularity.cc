<#
.SYNOPSIS
Automates the deployment integration of the Simulated Singularity C2 using GitHub Actions.

.DESCRIPTION
This script uses the GitHub CLI (gh) to:
1. Create a new GitHub repository for the Simulated Singularity project.
2. Initialize the local git repository and push the code to trigger the CI/CD pipeline.
3. Configure the required secrets (PROD_HOST, PROD_USER, PROD_SSH_KEY) for the deployment job.
#>

param (
    [Parameter(Mandatory=$false)][string]$RepoName = "simulated-singularity-c2",
    [Parameter(Mandatory=$false)][string]$Visibility = "private"
)

Write-Host "[SYS.LOG] Initializing GitHub CI/CD Deployment Integration..." -ForegroundColor Cyan

# 1. Verify GitHub CLI is installed and authenticated
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI (gh) is not installed. Please install it from https://cli.github.com/ and run 'gh auth login' before running this script."
    exit 1
}

$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "GitHub CLI is not authenticated. Please run 'gh auth login' first."
    exit 1
}

# 2. Check if git repository is initialized
if (-not (Test-Path ".git")) {
    Write-Host "[SYS.LOG] Initializing local git repository..." -ForegroundColor Yellow
    git init
    git branch -M main
    git add .
    git commit -m "Initial commit: Simulated Singularity C2 Architecture"
} else {
    Write-Host "[SYS.LOG] Local git repository detected." -ForegroundColor Green
}

# 3. Check if remote origin exists, otherwise create repo via gh
$remoteOrigin = git remote get-url origin 2>$null
if (-not $remoteOrigin) {
    Write-Host "[SYS.LOG] Creating GitHub repository '$RepoName' ($Visibility)..." -ForegroundColor Yellow
    gh repo create $RepoName --$Visibility --source=. --remote=origin --push
} else {
    Write-Host "[SYS.LOG] Remote repository already configured: $remoteOrigin" -ForegroundColor Green
}

# 4. Prompt for Production Secrets for the deployment workflow
Write-Host "`n[SYS.LOG] The CI/CD pipeline requires SSH secrets to deploy to the production node." -ForegroundColor Cyan
$setupSecrets = Read-Host "Do you want to configure production secrets now? (Y/N)"

if ($setupSecrets -match "^[yY]") {
    $prodHost = Read-Host "Enter Production Host IP or Domain (e.g., 203.0.113.50)"
    $prodUser = Read-Host "Enter Production SSH Username (e.g., root)"
    
    Write-Host "Please provide the path to your Production SSH Private Key (e.g., ~/.ssh/id_rsa):" -ForegroundColor Yellow
    $sshKeyPath = Read-Host "SSH Key Path"
    
    # Resolve the path for Windows
    $resolvedKeyPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($sshKeyPath)
    
    if (Test-Path $resolvedKeyPath) {
        Write-Host "[SYS.LOG] Setting secrets via gh CLI..." -ForegroundColor Yellow
        gh secret set PROD_HOST -b "$prodHost"
        gh secret set PROD_USER -b "$prodUser"
        gh secret set PROD_SSH_KEY -f "$resolvedKeyPath"
        Write-Host "[SYS.LOG] Secrets configured successfully." -ForegroundColor Green
    } else {
        Write-Error "SSH key file not found at $resolvedKeyPath. Secrets were not configured."
    }
} else {
    Write-Host "[SYS.LOG] Skipping secrets configuration. You must set PROD_HOST, PROD_USER, and PROD_SSH_KEY manually in the repository settings." -ForegroundColor Yellow
}

# 5. Push any pending changes to trigger the pipeline
Write-Host "`n[SYS.LOG] Pushing latest changes to 'main' branch to trigger GitHub Actions..." -ForegroundColor Cyan
git add .
git commit -m "chore: CI/CD automated deployment push"
git push -u origin main

Write-Host "`n[SYS.LOG] Deployment Integration Complete!" -ForegroundColor Green
Write-Host "You can monitor the workflow progress by running:" -ForegroundColor White
Write-Host "gh run watch" -ForegroundColor Magenta

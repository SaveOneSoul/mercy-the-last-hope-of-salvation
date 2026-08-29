param(
    [string]$ProjectId = "mercy-last-hope-rk-260817",
    [string]$Region = "asia-south1",
    [string]$ServiceName = "mercy-api",
    [string]$RuntimeServiceAccountName = "mercy-api-runtime",
    [string]$SecretName = "mercy-magisterium-api-key"
)

$ErrorActionPreference = "Stop"

function Invoke-GCloud {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    & gcloud @Args
    if ($LASTEXITCODE -ne 0) {
        throw "gcloud command failed: gcloud $($Args -join ' ')"
    }
}

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "Google Cloud CLI (gcloud) is not installed or is not on PATH."
}

$activeAccount = (& gcloud auth list --filter=status:ACTIVE --format="value(account)").Trim()
if (-not $activeAccount) {
    Write-Host "No active Google Cloud account found. Opening Google login..." -ForegroundColor Yellow
    Invoke-GCloud auth login
    $activeAccount = (& gcloud auth list --filter=status:ACTIVE --format="value(account)").Trim()
}

Write-Host "`n=== Mercy Catholic AI - Google Cloud deployment ===" -ForegroundColor Cyan
Write-Host "Project : $ProjectId"
Write-Host "Region  : $Region"
Write-Host "Service : $ServiceName"
Write-Host "Account : $activeAccount"

Invoke-GCloud config set project $ProjectId

Write-Host "`nEnabling required Google Cloud APIs..." -ForegroundColor Cyan
Invoke-GCloud services enable `
    run.googleapis.com `
    cloudbuild.googleapis.com `
    artifactregistry.googleapis.com `
    secretmanager.googleapis.com `
    iam.googleapis.com

$runtimeEmail = "$RuntimeServiceAccountName@$ProjectId.iam.gserviceaccount.com"
Write-Host "`nPreparing dedicated Cloud Run runtime service account..." -ForegroundColor Cyan
& gcloud iam service-accounts describe $runtimeEmail --project $ProjectId *> $null
if ($LASTEXITCODE -ne 0) {
    Invoke-GCloud iam service-accounts create $RuntimeServiceAccountName `
        --project $ProjectId `
        --display-name "Mercy API Cloud Run runtime"
} else {
    Write-Host "Runtime service account already exists: $runtimeEmail"
}

$deployerMember = if ($activeAccount -like "*gserviceaccount.com") {
    "serviceAccount:$activeAccount"
} else {
    "user:$activeAccount"
}

Write-Host "Granting the active deployer permission to attach the runtime identity..." -ForegroundColor Cyan
Invoke-GCloud iam service-accounts add-iam-policy-binding $runtimeEmail `
    --project $ProjectId `
    --member $deployerMember `
    --role roles/iam.serviceAccountUser

& gcloud secrets describe $SecretName --project $ProjectId *> $null
$secretExists = ($LASTEXITCODE -eq 0)
$addSecretVersion = $true

if ($secretExists) {
    Write-Host "`nSecret already exists: $SecretName" -ForegroundColor Green
    $choice = Read-Host "Add a new Magisterium API-key version now? (y/N)"
    $addSecretVersion = ($choice -match '^[Yy]$')
}

if (-not $secretExists -or $addSecretVersion) {
    Write-Host "`nEnter the Magisterium API key. It will NOT be printed or committed to GitHub." -ForegroundColor Yellow
    $secureKey = Read-Host "MAGISTERIUM_API_KEY" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    $plainKey = $null
    $tempSecretFile = Join-Path ([System.IO.Path]::GetTempPath()) ("mercy-magisterium-" + [guid]::NewGuid().ToString("N") + ".txt")
    try {
        $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
        if ([string]::IsNullOrWhiteSpace($plainKey)) {
            throw "The Magisterium API key cannot be empty."
        }
        [System.IO.File]::WriteAllText($tempSecretFile, $plainKey, [System.Text.UTF8Encoding]::new($false))

        if (-not $secretExists) {
            Invoke-GCloud secrets create $SecretName `
                --project $ProjectId `
                --replication-policy automatic `
                --data-file $tempSecretFile
            $secretExists = $true
        } else {
            Invoke-GCloud secrets versions add $SecretName `
                --project $ProjectId `
                --data-file $tempSecretFile
        }
    }
    finally {
        if ($bstr -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
        $plainKey = $null
        if (Test-Path $tempSecretFile) {
            Remove-Item $tempSecretFile -Force
        }
    }
}

if (-not $secretExists) {
    throw "The Secret Manager secret $SecretName does not exist. Deployment cannot continue."
}

Write-Host "`nGranting only the runtime service account access to the Magisterium secret..." -ForegroundColor Cyan
Invoke-GCloud secrets add-iam-policy-binding $SecretName `
    --project $ProjectId `
    --member "serviceAccount:$runtimeEmail" `
    --role roles/secretmanager.secretAccessor

Write-Host "`nDeploying cloud-backend to Cloud Run from source..." -ForegroundColor Cyan
Push-Location $PSScriptRoot
try {
    Invoke-GCloud run deploy $ServiceName `
        --project $ProjectId `
        --region $Region `
        --platform managed `
        --source . `
        --allow-unauthenticated `
        --service-account $runtimeEmail `
        --set-secrets "MAGISTERIUM_API_KEY=${SecretName}:latest" `
        --set-env-vars "CORS_ORIGINS=https://saveonesoul.github.io,MAGISTERIUM_MODEL=magisterium-1,ENABLE_DOCS=false,DATABASE_URL=sqlite:////tmp/mercy.db" `
        --memory 512Mi `
        --cpu 1 `
        --concurrency 40 `
        --max-instances 3 `
        --timeout 60
}
finally {
    Pop-Location
}

$serviceUrl = (& gcloud run services describe $ServiceName `
    --project $ProjectId `
    --region $Region `
    --format="value(status.url)").Trim()

if (-not $serviceUrl) {
    throw "Deployment finished but the Cloud Run service URL could not be read."
}

Write-Host "`nCloud Run service URL:" -ForegroundColor Green
Write-Host $serviceUrl

Write-Host "`nChecking /health ..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "$serviceUrl/health" -Method Get -TimeoutSec 30
    $health | ConvertTo-Json -Depth 8
} catch {
    Write-Warning "The deployment completed, but the health request failed: $($_.Exception.Message)"
}

Write-Host "`nTesting Catholic AI..." -ForegroundColor Cyan
try {
    $testBody = @{ message = "What does the Catholic Church teach about the Eucharist?"; language = "en" } | ConvertTo-Json
    $test = Invoke-RestMethod -Uri "$serviceUrl/api/chat" -Method Post -ContentType "application/json" -Body $testBody -TimeoutSec 60
    Write-Host "Provider: $($test.provider)" -ForegroundColor Green
    Write-Host "Reply received: $([bool]$test.reply)"
    Write-Host "Sources returned: $(@($test.sources).Count)"
} catch {
    Write-Warning "Cloud Run is reachable, but the Magisterium AI test failed: $($_.Exception.Message)"
}

Write-Host "`nNEXT STEP" -ForegroundColor Yellow
Write-Host "Set javascript/analytics-config.json -> mercy_api_base to:"
Write-Host "  $serviceUrl"
Write-Host "Then commit/push that public URL. Never place MAGISTERIUM_API_KEY in GitHub."
Write-Host "`nNote: DATABASE_URL currently uses temporary Cloud Run SQLite storage. Catholic AI is production-ready with respect to secret handling, but Save One Soul counters and submitted prayer data need a durable production database before relying on them across Cloud Run restarts."

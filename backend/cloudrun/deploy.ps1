param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,

    [Parameter(Mandatory=$true)]
    [string]$GitHubOrigin,

    [string]$Region = "asia-south1",
    [string]$ServiceName = "mercy-catholic-api",
    [string]$OpenAISecretName = "mercy-openai-api-key"
)

$ErrorActionPreference = "Stop"

function Invoke-Gcloud {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)
    & gcloud @Args
    if ($LASTEXITCODE -ne 0) { throw "gcloud command failed: gcloud $($Args -join ' ')" }
}

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "Google Cloud CLI (gcloud) is not installed or is not in PATH."
}

if ($GitHubOrigin.EndsWith('/')) { $GitHubOrigin = $GitHubOrigin.TrimEnd('/') }
if (-not $GitHubOrigin.StartsWith('https://')) {
    throw "GitHubOrigin must be an HTTPS origin such as https://USERNAME.github.io"
}

Write-Host "`n== Mercy Catholic AI: Google Cloud Run deployment ==" -ForegroundColor Cyan
Write-Host "Project: $ProjectId"
Write-Host "Region:  $Region"
Write-Host "Origin:  $GitHubOrigin`n"

Invoke-Gcloud config set project $ProjectId
Invoke-Gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com iam.googleapis.com

$runtimeSaName = "$ServiceName-runtime"
$runtimeSa = "$runtimeSaName@$ProjectId.iam.gserviceaccount.com"
& gcloud iam service-accounts describe $runtimeSa --project $ProjectId *> $null
if ($LASTEXITCODE -ne 0) {
    Invoke-Gcloud iam service-accounts create $runtimeSaName --project $ProjectId --display-name "Mercy Catholic AI Cloud Run runtime"
}

& gcloud secrets describe $OpenAISecretName --project $ProjectId *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "The OpenAI secret does not exist yet." -ForegroundColor Yellow
    $secure = Read-Host "Paste your OpenAI API key (input is hidden)" -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
        $tmp = [System.IO.Path]::GetTempFileName()
        [System.IO.File]::WriteAllText($tmp, $plain, [System.Text.UTF8Encoding]::new($false))
        Invoke-Gcloud secrets create $OpenAISecretName --project $ProjectId --replication-policy automatic --data-file $tmp
    }
    finally {
        if ($ptr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
        if ($tmp -and (Test-Path $tmp)) { Remove-Item $tmp -Force }
        $plain = $null
    }
}

Invoke-Gcloud secrets add-iam-policy-binding $OpenAISecretName --project $ProjectId --member "serviceAccount:$runtimeSa" --role roles/secretmanager.secretAccessor

$backendDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $backendDir
try {
    Invoke-Gcloud run deploy $ServiceName `
        --project $ProjectId `
        --source . `
        --region $Region `
        --platform managed `
        --allow-unauthenticated `
        --service-account $runtimeSa `
        --cpu 1 `
        --memory 512Mi `
        --min-instances 0 `
        --max-instances 3 `
        --concurrency 40 `
        --timeout 60 `
        --set-env-vars "ENVIRONMENT=production,ALLOWED_ORIGINS=$GitHubOrigin,PERSIST_CONTACT_MESSAGES=false,OPENAI_MODEL=gpt-5.6-luna,OPENAI_CLASSIFIER_MODEL=gpt-5.6-luna,RATE_LIMIT_PER_MINUTE=20" `
        --set-secrets "OPENAI_API_KEY=$OpenAISecretName`:latest"
}
finally {
    Pop-Location
}

$serviceUrl = (& gcloud run services describe $ServiceName --project $ProjectId --region $Region --format "value(status.url)").Trim()
if (-not $serviceUrl) { throw "Deployment completed but the Cloud Run URL could not be read." }

$configPath = (Resolve-Path (Join-Path $PSScriptRoot "..\..\javascript\config.js")).Path
$config = Get-Content $configPath -Raw
$config = [regex]::Replace($config, 'apiBaseUrl:\s*"[^"]*"', "apiBaseUrl: `"$serviceUrl`"")
$config = [regex]::Replace($config, 'enableRemoteAI:\s*(true|false)', 'enableRemoteAI: true')
[System.IO.File]::WriteAllText($configPath, $config, [System.Text.UTF8Encoding]::new($false))

Write-Host "`nDeployment complete." -ForegroundColor Green
Write-Host "Cloud Run URL: $serviceUrl"
Write-Host "Health check:  $serviceUrl/health"
Write-Host "Frontend config updated: $configPath"
Write-Host "`nNext: test the API, then commit/push the updated frontend to GitHub Pages." -ForegroundColor Cyan

[CmdletBinding(PositionalBinding = $false)]
param(
    [ValidateNotNullOrEmpty()][string]$ProjectId = "mercy-last-hope-rk-260817",
    [ValidateNotNullOrEmpty()][string]$Region = "asia-south1",
    [ValidateNotNullOrEmpty()][string]$ServiceName = "mercy-api",
    [ValidateNotNullOrEmpty()][string]$RuntimeServiceAccountName = "mercy-api-runtime",
    [ValidateNotNullOrEmpty()][string]$SecretName = "mercy-magisterium-api-key",
    [ValidateNotNullOrEmpty()][string]$DbInstanceName = "mercy-postgres",
    [ValidateNotNullOrEmpty()][string]$DbName = "mercy",
    [ValidateNotNullOrEmpty()][string]$DbUser = "mercy_app",
    [ValidateNotNullOrEmpty()][string]$DbPasswordSecretName = "mercy-db-password",
    [ValidateNotNullOrEmpty()][string]$AdminPasswordSecretName = "mercy-admin-password",
    [ValidateNotNullOrEmpty()][string]$AdminSessionSecretName = "mercy-admin-session-secret",
    [string]$CmsBucketName = "",
    [ValidateNotNullOrEmpty()][string]$DbTier = "db-f1-micro",
    [switch]$RotateDatabasePassword,
    [switch]$RotateAdminPassword
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($CmsBucketName)) {
    $CmsBucketName = "$ProjectId-mercy-cms-assets"
}

function Invoke-GCloud {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    & gcloud @Args
    if ($LASTEXITCODE -ne 0) {
        throw "gcloud command failed: gcloud $($Args -join ' ')"
    }
}

function Test-GCloudResource {
    param([Parameter(Mandatory = $true)][string[]]$Args)
    & gcloud @Args *> $null
    return ($LASTEXITCODE -eq 0)
}

function New-StrongSecret {
    param([int]$Bytes = 32)
    $buffer = New-Object byte[] $Bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($buffer)
    return [Convert]::ToBase64String($buffer).TrimEnd('=').Replace('+', 'A').Replace('/', 'B')
}

function New-StrongDatabasePassword {
    return "Mcy!$(New-StrongSecret -Bytes 32)"
}

function Convert-SecureToPlain {
    param([Parameter(Mandatory = $true)][System.Security.SecureString]$SecureValue)
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    }
    finally {
        if ($bstr -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
    }
}

function Write-SecretVersion {
    param(
        [Parameter(Mandatory = $true)][string]$Secret,
        [Parameter(Mandatory = $true)][string]$Value,
        [Parameter(Mandatory = $true)][bool]$Exists
    )

    $tempFile = Join-Path ([System.IO.Path]::GetTempPath()) ("mercy-secret-" + [guid]::NewGuid().ToString("N") + ".txt")
    try {
        [System.IO.File]::WriteAllText($tempFile, $Value, [System.Text.UTF8Encoding]::new($false))
        if ($Exists) {
            Invoke-GCloud secrets versions add $Secret --project $ProjectId --data-file $tempFile
        } else {
            Invoke-GCloud secrets create $Secret --project $ProjectId --replication-policy automatic --data-file $tempFile
        }
    }
    finally {
        if (Test-Path $tempFile) {
            Remove-Item $tempFile -Force
        }
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

Write-Host "`n=== Mercy production backend + Admin CMS deployment ===" -ForegroundColor Cyan
Write-Host "Project        : $ProjectId"
Write-Host "Region         : $Region"
Write-Host "Cloud Run      : $ServiceName"
Write-Host "Cloud SQL      : $DbInstanceName"
Write-Host "Database       : $DbName"
Write-Host "Database user  : $DbUser"
Write-Host "CMS bucket     : $CmsBucketName"
Write-Host "Account        : $activeAccount"

Invoke-GCloud config set project $ProjectId

Write-Host "`nEnabling required Google Cloud APIs..." -ForegroundColor Cyan
Invoke-GCloud services enable `
    run.googleapis.com `
    cloudbuild.googleapis.com `
    artifactregistry.googleapis.com `
    secretmanager.googleapis.com `
    iam.googleapis.com `
    sqladmin.googleapis.com `
    storage.googleapis.com

$runtimeEmail = "$RuntimeServiceAccountName@$ProjectId.iam.gserviceaccount.com"
Write-Host "`nPreparing dedicated Cloud Run runtime service account..." -ForegroundColor Cyan
if (-not (Test-GCloudResource @("iam", "service-accounts", "describe", $runtimeEmail, "--project", $ProjectId))) {
    Invoke-GCloud iam service-accounts create $RuntimeServiceAccountName `
        --project $ProjectId `
        --display-name "Mercy API Cloud Run runtime"
} else {
    Write-Host "Runtime service account already exists: $runtimeEmail" -ForegroundColor Green
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
    --role roles/iam.serviceAccountUser `
    --quiet

Write-Host "`nPreparing Magisterium API secret..." -ForegroundColor Cyan
$magisteriumSecretExists = Test-GCloudResource @("secrets", "describe", $SecretName, "--project", $ProjectId)
$addSecretVersion = -not $magisteriumSecretExists
if ($magisteriumSecretExists) {
    Write-Host "Secret already exists: $SecretName" -ForegroundColor Green
    $choice = Read-Host "Add a new Magisterium API-key version now? (y/N)"
    $addSecretVersion = ($choice -match '^[Yy]$')
}

if ($addSecretVersion) {
    Write-Host "Enter the Magisterium API key. It will NOT be printed or committed to GitHub." -ForegroundColor Yellow
    $secureKey = Read-Host "MAGISTERIUM_API_KEY" -AsSecureString
    $plainKey = Convert-SecureToPlain $secureKey
    try {
        if ([string]::IsNullOrWhiteSpace($plainKey)) {
            throw "The Magisterium API key cannot be empty."
        }
        Write-SecretVersion -Secret $SecretName -Value $plainKey -Exists $magisteriumSecretExists
        $magisteriumSecretExists = $true
    }
    finally {
        $plainKey = $null
    }
}

if (-not $magisteriumSecretExists) {
    throw "The Secret Manager secret $SecretName does not exist. Deployment cannot continue."
}

Write-Host "`nPreparing durable Cloud SQL PostgreSQL..." -ForegroundColor Cyan
$dbInstanceExists = Test-GCloudResource @("sql", "instances", "describe", $DbInstanceName, "--project", $ProjectId)
if (-not $dbInstanceExists) {
    Write-Host "Creating Cloud SQL instance. This can take several minutes..." -ForegroundColor Yellow
    Invoke-GCloud sql instances create $DbInstanceName `
        --project $ProjectId `
        --database-version POSTGRES_15 `
        --region $Region `
        --tier $DbTier `
        --storage-type SSD `
        --storage-size 10 `
        --storage-auto-increase `
        --availability-type zonal `
        --backup-start-time 02:00 `
        --enable-point-in-time-recovery `
        --quiet
} else {
    Write-Host "Cloud SQL instance already exists: $DbInstanceName" -ForegroundColor Green
}

$dbExists = Test-GCloudResource @("sql", "databases", "describe", $DbName, "--instance", $DbInstanceName, "--project", $ProjectId)
if (-not $dbExists) {
    Invoke-GCloud sql databases create $DbName --instance $DbInstanceName --project $ProjectId
} else {
    Write-Host "Database already exists: $DbName" -ForegroundColor Green
}

$dbPasswordSecretExists = Test-GCloudResource @("secrets", "describe", $DbPasswordSecretName, "--project", $ProjectId)
$dbUsers = @(& gcloud sql users list --instance $DbInstanceName --project $ProjectId --format="value(name)")
$dbUserExists = ($dbUsers -contains $DbUser)
$mustRotateDbPassword = $RotateDatabasePassword.IsPresent -or (-not $dbPasswordSecretExists) -or (-not $dbUserExists)

if ($mustRotateDbPassword) {
    $dbPassword = New-StrongDatabasePassword
    try {
        if ($dbUserExists) {
            Invoke-GCloud sql users set-password $DbUser `
                --instance $DbInstanceName `
                --project $ProjectId `
                --password $dbPassword
        } else {
            Invoke-GCloud sql users create $DbUser `
                --instance $DbInstanceName `
                --project $ProjectId `
                --password $dbPassword
            $dbUserExists = $true
        }
        Write-SecretVersion -Secret $DbPasswordSecretName -Value $dbPassword -Exists $dbPasswordSecretExists
        $dbPasswordSecretExists = $true
    }
    finally {
        $dbPassword = $null
    }
} else {
    Write-Host "Database user and password secret already exist; password not rotated." -ForegroundColor Green
}

Write-Host "`nPreparing private Admin Dashboard credentials..." -ForegroundColor Cyan
$adminPasswordSecretExists = Test-GCloudResource @("secrets", "describe", $AdminPasswordSecretName, "--project", $ProjectId)
if ((-not $adminPasswordSecretExists) -or $RotateAdminPassword.IsPresent) {
    Write-Host "Choose a strong password for the Mercy Admin Dashboard." -ForegroundColor Yellow
    $secureAdminPassword = Read-Host "ADMIN PASSWORD (minimum 12 characters)" -AsSecureString
    $adminPassword = Convert-SecureToPlain $secureAdminPassword
    try {
        if ([string]::IsNullOrWhiteSpace($adminPassword) -or $adminPassword.Length -lt 12) {
            throw "Admin password must contain at least 12 characters."
        }
        Write-SecretVersion -Secret $AdminPasswordSecretName -Value $adminPassword -Exists $adminPasswordSecretExists
        $adminPasswordSecretExists = $true
    }
    finally {
        $adminPassword = $null
    }
} else {
    Write-Host "Admin password secret already exists; password not rotated." -ForegroundColor Green
}

$adminSessionSecretExists = Test-GCloudResource @("secrets", "describe", $AdminSessionSecretName, "--project", $ProjectId)
if (-not $adminSessionSecretExists) {
    $adminSessionSecret = New-StrongSecret -Bytes 48
    try {
        Write-SecretVersion -Secret $AdminSessionSecretName -Value $adminSessionSecret -Exists $false
        $adminSessionSecretExists = $true
    }
    finally {
        $adminSessionSecret = $null
    }
} else {
    Write-Host "Admin session-signing secret already exists." -ForegroundColor Green
}

Write-Host "`nPreparing Cloud Storage for CMS images..." -ForegroundColor Cyan
$bucketUri = "gs://$CmsBucketName"
$bucketExists = Test-GCloudResource @("storage", "buckets", "describe", $bucketUri, "--project", $ProjectId)
if (-not $bucketExists) {
    Invoke-GCloud storage buckets create $bucketUri `
        --project $ProjectId `
        --location $Region `
        --uniform-bucket-level-access
} else {
    Write-Host "CMS image bucket already exists: $bucketUri" -ForegroundColor Green
}

# Public read is intentional: uploaded CMS images are public website assets.
Invoke-GCloud storage buckets add-iam-policy-binding $bucketUri `
    --member allUsers `
    --role roles/storage.objectViewer
Invoke-GCloud storage buckets add-iam-policy-binding $bucketUri `
    --member "serviceAccount:$runtimeEmail" `
    --role roles/storage.objectAdmin

$instanceConnectionName = (& gcloud sql instances describe $DbInstanceName `
    --project $ProjectId `
    --format="value(connectionName)").Trim()
if (-not $instanceConnectionName) {
    throw "Cloud SQL instance connection name could not be read."
}
$instanceUnixSocket = "/cloudsql/$instanceConnectionName"

Write-Host "`nGranting runtime identity only the permissions it needs..." -ForegroundColor Cyan
Invoke-GCloud projects add-iam-policy-binding $ProjectId `
    --member "serviceAccount:$runtimeEmail" `
    --role roles/cloudsql.client `
    --quiet

foreach ($secretToGrant in @($SecretName, $DbPasswordSecretName, $AdminPasswordSecretName, $AdminSessionSecretName)) {
    Invoke-GCloud secrets add-iam-policy-binding $secretToGrant `
        --project $ProjectId `
        --member "serviceAccount:$runtimeEmail" `
        --role roles/secretmanager.secretAccessor `
        --quiet
}

Write-Host "`nDeploying cloud-backend to Cloud Run with Cloud SQL and Admin CMS..." -ForegroundColor Cyan
Push-Location $PSScriptRoot
try {
    Invoke-GCloud run deploy $ServiceName `
        --project $ProjectId `
        --region $Region `
        --platform managed `
        --source . `
        --allow-unauthenticated `
        --service-account $runtimeEmail `
        --add-cloudsql-instances $instanceConnectionName `
        --set-secrets "MAGISTERIUM_API_KEY=${SecretName}:latest,DB_PASS=${DbPasswordSecretName}:latest,ADMIN_PASSWORD=${AdminPasswordSecretName}:latest,ADMIN_SESSION_SECRET=${AdminSessionSecretName}:latest" `
        --set-env-vars "CORS_ORIGINS=https://saveonesoul.github.io,PUBLIC_SITE_BASE=https://saveonesoul.github.io/mercy-the-last-hope-of-salvation,MAGISTERIUM_MODEL=magisterium-1,MAGISTERIUM_TIMEOUT_SECONDS=90,ENABLE_DOCS=false,DB_USER=$DbUser,DB_NAME=$DbName,INSTANCE_UNIX_SOCKET=$instanceUnixSocket,DB_POOL_SIZE=5,DB_MAX_OVERFLOW=2,DB_POOL_RECYCLE_SECONDS=1800,CMS_BUCKET=$CmsBucketName" `
        --memory 512Mi `
        --cpu 1 `
        --concurrency 40 `
        --max-instances 3 `
        --timeout 120 `
        --quiet
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
$health = Invoke-RestMethod -Uri "$serviceUrl/health" -Method Get -TimeoutSec 30
$health | ConvertTo-Json -Depth 8
if (-not $health.database.reachable) {
    throw "Deployment completed, but Cloud SQL is not reachable from the service."
}
if (-not $health.database.durable) {
    throw "Deployment completed, but the API is not reporting durable database storage."
}
if (-not $health.admin_cms.configured) {
    throw "Deployment completed, but Admin CMS authentication is not configured."
}
if (-not $health.admin_cms.bucket_configured) {
    throw "Deployment completed, but the CMS image bucket is not configured."
}

Write-Host "`nChecking Save One Soul aggregate endpoint ..." -ForegroundColor Cyan
$stats = Invoke-RestMethod -Uri "$serviceUrl/api/save-one-soul/stats" -Method Get -TimeoutSec 30
$stats | ConvertTo-Json -Depth 8

Write-Host "`nTesting Catholic AI..." -ForegroundColor Cyan
try {
    $testBody = @{ message = "What does the Catholic Church teach about the Eucharist?"; language = "en" } | ConvertTo-Json
    $test = Invoke-RestMethod -Uri "$serviceUrl/api/chat" -Method Post -ContentType "application/json" -Body $testBody -TimeoutSec 120
    Write-Host "Provider: $($test.provider)" -ForegroundColor Green
    Write-Host "Reply received: $([bool]$test.reply)"
    Write-Host "Sources returned: $(@($test.sources).Count)"
} catch {
    Write-Warning "Cloud Run and Cloud SQL are healthy, but the Magisterium AI test failed: $($_.Exception.Message)"
}

Write-Host "`nPRODUCTION BACKEND + ADMIN CMS READY" -ForegroundColor Green
Write-Host "Cloud SQL connection : $instanceConnectionName"
Write-Host "Database             : $DbName"
Write-Host "CMS image bucket     : $bucketUri"
Write-Host "Backend              : $serviceUrl"
Write-Host "Admin Dashboard      : $serviceUrl/admin"
Write-Host "Frontend origin      : https://saveonesoul.github.io"
Write-Host "`nUse the admin password you chose above to sign in."
Write-Host "Editorial text, links and images should now be changed through the Admin Dashboard; source-code edits remain for technical changes only."

param(
    [Parameter(Mandatory=$true)]
    [string]$ServiceUrl
)
$ErrorActionPreference = "Stop"
$ServiceUrl = $ServiceUrl.TrimEnd('/')

Write-Host "Testing health..." -ForegroundColor Cyan
Invoke-RestMethod "$ServiceUrl/health" | ConvertTo-Json -Depth 6

Write-Host "`nTesting Catholic question..." -ForegroundColor Cyan
$allowed = Invoke-RestMethod -Method Post -Uri "$ServiceUrl/api/chat" -ContentType "application/json" -Body (@{
    message = "What does the Catholic Church teach about the Eucharist?"
    client_id = "cloudrun-test"
} | ConvertTo-Json)
$allowed | ConvertTo-Json -Depth 8

Write-Host "`nTesting non-Catholic refusal..." -ForegroundColor Cyan
$blocked = Invoke-RestMethod -Method Post -Uri "$ServiceUrl/api/chat" -ContentType "application/json" -Body (@{
    message = "Write Python code for a weather app"
    client_id = "cloudrun-test"
} | ConvertTo-Json)
$blocked | ConvertTo-Json -Depth 8

if ($blocked.scope -ne "out_of_scope") {
    throw "Catholic-only guard test failed: non-Catholic question was not rejected."
}
Write-Host "`nCatholic-only guard is working." -ForegroundColor Green

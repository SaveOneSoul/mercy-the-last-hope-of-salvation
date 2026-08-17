param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,

    [string]$SecretName = "mercy-gemini-api-key",
    [string]$SecretVersion = "1",
    [string]$Model = "gemini-3.6-flash"
)

$ErrorActionPreference = "Stop"

$env:GEMINI_API_KEY = (
    gcloud secrets versions access $SecretVersion `
        --secret=$SecretName `
        --project=$ProjectId
).Trim()

try {
    $headers = @{
        "x-goog-api-key" = $env:GEMINI_API_KEY
        "Content-Type"   = "application/json"
    }

    $body = @{
        contents = @(
            @{
                parts = @(
                    @{ text = "Reply only with the word OK." }
                )
            }
        )
    } | ConvertTo-Json -Depth 6

    try {
        $response = Invoke-RestMethod `
            -Method Post `
            -Uri "https://generativelanguage.googleapis.com/v1beta/models/$Model`:generateContent" `
            -Headers $headers `
            -Body $body

        $response.candidates[0].content.parts[0].text
    }
    catch {
        if ($_.ErrorDetails.Message) {
            $_.ErrorDetails.Message
        } else {
            throw
        }
    }
}
finally {
    Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
}

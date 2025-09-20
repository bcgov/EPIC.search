# Upload and Publish App Services Runbooks
# This script uploads PowerShell content to the runbooks and publishes them

param(
    [Parameter(Mandatory=$true)]
    [string]$AutomationAccountName,
    
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName
)

Write-Host "=== Uploading and Publishing App Services Runbooks ===" -ForegroundColor Green

# Upload and publish Start-AppServices runbook
Write-Host ""
Write-Host "Processing Start-AppServices runbook..." -ForegroundColor Yellow

Write-Host "  Uploading content from Start-AppServices.ps1"
az automation runbook replace-content `
    --automation-account-name $AutomationAccountName `
    --resource-group $ResourceGroupName `
    --name "Start-AppServices" `
    --content "@Start-AppServices.ps1"

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Content uploaded successfully" -ForegroundColor Green
    
    Write-Host "  Publishing runbook..."
    az automation runbook publish `
        --automation-account-name $AutomationAccountName `
        --resource-group $ResourceGroupName `
        --name "Start-AppServices"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Start-AppServices published successfully" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Failed to publish Start-AppServices" -ForegroundColor Red
    }
} else {
    Write-Host "  ❌ Failed to upload Start-AppServices content" -ForegroundColor Red
}

# Upload and publish Stop-AppServices runbook
Write-Host ""
Write-Host "Processing Stop-AppServices runbook..." -ForegroundColor Yellow

Write-Host "  Uploading content from Stop-AppServices.ps1"
az automation runbook replace-content `
    --automation-account-name $AutomationAccountName `
    --resource-group $ResourceGroupName `
    --name "Stop-AppServices" `
    --content "@Stop-AppServices.ps1"

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Content uploaded successfully" -ForegroundColor Green
    
    Write-Host "  Publishing runbook..."
    az automation runbook publish `
        --automation-account-name $AutomationAccountName `
        --resource-group $ResourceGroupName `
        --name "Stop-AppServices"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Stop-AppServices published successfully" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Failed to publish Stop-AppServices" -ForegroundColor Red
    }
} else {
    Write-Host "  ❌ Failed to upload Stop-AppServices content" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎉 App Services runbooks are ready!" -ForegroundColor Green
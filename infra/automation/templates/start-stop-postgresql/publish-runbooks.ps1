# Upload and Publish PostgreSQL Runbooks
# This script uploads PowerShell content to the runbooks and publishes them

param(
    [Parameter(Mandatory=$true)]
    [string]$AutomationAccountName,
    
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName
)

Write-Host "=== Uploading and Publishing PostgreSQL Runbooks ===" -ForegroundColor Green

# Upload and publish Start-PostgreSQL runbook
Write-Host ""
Write-Host "Processing Start-PostgreSQL runbook..." -ForegroundColor Yellow

Write-Host "  Uploading content from Start-PostgreSQL.ps1"
az automation runbook replace-content `
    --automation-account-name $AutomationAccountName `
    --resource-group $ResourceGroupName `
    --name "Start-PostgreSQL" `
    --content "@Start-PostgreSQL.ps1"

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Content uploaded successfully" -ForegroundColor Green
    
    Write-Host "  Publishing runbook..."
    az automation runbook publish `
        --automation-account-name $AutomationAccountName `
        --resource-group $ResourceGroupName `
        --name "Start-PostgreSQL"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Start-PostgreSQL published successfully" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Failed to publish Start-PostgreSQL" -ForegroundColor Red
    }
} else {
    Write-Host "  ❌ Failed to upload Start-PostgreSQL content" -ForegroundColor Red
}

# Upload and publish Stop-PostgreSQL runbook
Write-Host ""
Write-Host "Processing Stop-PostgreSQL runbook..." -ForegroundColor Yellow

Write-Host "  Uploading content from Stop-PostgreSQL.ps1"
az automation runbook replace-content `
    --automation-account-name $AutomationAccountName `
    --resource-group $ResourceGroupName `
    --name "Stop-PostgreSQL" `
    --content "@Stop-PostgreSQL.ps1"

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Content uploaded successfully" -ForegroundColor Green
    
    Write-Host "  Publishing runbook..."
    az automation runbook publish `
        --automation-account-name $AutomationAccountName `
        --resource-group $ResourceGroupName `
        --name "Stop-PostgreSQL"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Stop-PostgreSQL published successfully" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Failed to publish Stop-PostgreSQL" -ForegroundColor Red
    }
} else {
    Write-Host "  ❌ Failed to upload Stop-PostgreSQL content" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎉 PostgreSQL runbooks are ready!" -ForegroundColor Green
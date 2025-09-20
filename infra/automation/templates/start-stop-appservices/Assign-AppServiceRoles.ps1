# Tag-based App Service Role Assignment Script
# Assigns Website Contributor role to App Services with specific tags (optional)

param(
    [Parameter(Mandatory=$true)]
    [string]$PrincipalId,
    
    [string]$ResourceGroupName = "rg-myproject-apps",
    [string]$SubscriptionName = "",
    [string]$TagName = "",
    [string]$TagValue = ""
)

Write-Host "=== App Service Role Assignment Script ===" -ForegroundColor Green

# Switch to the correct subscription if specified
if ($SubscriptionName) {
    Write-Host "Switching to subscription: $SubscriptionName"
    az account set --subscription $SubscriptionName
    
    # Verify subscription
    $currentSub = az account show --query name --output tsv
    Write-Host "Current subscription: $currentSub"
}

# Find App Services based on criteria
Write-Host "Finding App Services in resource group: $ResourceGroupName" -ForegroundColor Yellow
$allAppServices = az resource list --resource-group $ResourceGroupName --resource-type "Microsoft.Web/sites" --query "[].{Name:name, Id:id, Tags:tags}" | ConvertFrom-Json

if ($TagName -and $TagValue) {
    Write-Host "Filtering by tag: $TagName = $TagValue" -ForegroundColor Yellow
    $appServices = $allAppServices | Where-Object { $_.Tags.$TagName -eq $TagValue }
} else {
    Write-Host "No tags specified - using ALL App Services" -ForegroundColor Yellow
    $appServices = $allAppServices
}

# Check if any App Services were found
if (-not $appServices -or $appServices.Count -eq 0) {
    Write-Host "No App Services found matching criteria" -ForegroundColor Red
    if ($TagName -and $TagValue) {
        Write-Host "Try running without tags to see all App Services in the resource group" -ForegroundColor Cyan
    }
    exit 1
}

Write-Host "Found $($appServices.Count) App Services:" -ForegroundColor Green
foreach ($app in $appServices) {
    Write-Host "  $($app.Name)" -ForegroundColor Cyan
}

# Confirm before proceeding
Write-Host ""
$confirm = Read-Host "Assign Website Contributor role to these App Services? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Operation cancelled" -ForegroundColor Red
    exit 0
}

# Assign Website Contributor role to each App Service
Write-Host ""
Write-Host "Assigning roles..." -ForegroundColor Green

$successCount = 0
$errorCount = 0

foreach ($appService in $appServices) {
    try {
        Write-Host "  Assigning role to: $($appService.Name)"
        
        az role assignment create --assignee $PrincipalId --role "Website Contributor" --scope $appService.Id --output none
            
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    Success" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host "    Failed" -ForegroundColor Red
            $errorCount++
        }
    }
    catch {
        Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Red
        $errorCount++
    }
}

# Check for authentication issues
if ($errorCount -gt 0) {
    Write-Host ""
    Write-Host "💡 If you see Microsoft Graph authentication errors:" -ForegroundColor Cyan
    Write-Host "   1. az logout" -ForegroundColor Cyan
    Write-Host "   2. az login --scope https://graph.microsoft.com//.default" -ForegroundColor Cyan
    Write-Host "   3. az account set --subscription '$SubscriptionName'" -ForegroundColor Cyan
    Write-Host "   4. Re-run this script" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "   Note: Switching subscriptions does NOT refresh Graph tokens!" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Green
Write-Host "Successful assignments: $successCount" -ForegroundColor Green
Write-Host "Failed assignments: $errorCount" -ForegroundColor Red

# Verify assignments
Write-Host ""
Write-Host "Verifying role assignments..." -ForegroundColor Yellow
az role assignment list --assignee $PrincipalId --query "[?roleDefinitionName=='Website Contributor'].{PrincipalId:principalId, Role:roleDefinitionName, Scope:scope}" --output table

Write-Host ""
Write-Host "Role assignment completed!" -ForegroundColor Green
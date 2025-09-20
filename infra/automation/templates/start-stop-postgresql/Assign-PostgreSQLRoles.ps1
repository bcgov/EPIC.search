# Tag-based PostgreSQL Role Assignment Script
# Assigns PostgreSQL Flexible Server Operator role to PostgreSQL servers with specific tags (optional)

param(
    [Parameter(Mandatory=$true)]
    [string]$PrincipalId,
    
    [string]$ResourceGroupName = "rg-myproject-apps",
    [string]$SubscriptionName = "",
    [string]$TagName = "",
    [string]$TagValue = "",
    [string]$EnvironmentSuffix = "Dev",
    [string]$BaseRoleName = "PostgreSQL Flexible Server Operator"
)

$CustomRoleName = "$BaseRoleName - $EnvironmentSuffix"

Write-Host "=== PostgreSQL Role Assignment Script ===" -ForegroundColor Green
Write-Host "Using custom role: $CustomRoleName" -ForegroundColor Cyan

# Switch to the correct subscription if specified
if ($SubscriptionName) {
    Write-Host "Switching to subscription: $SubscriptionName"
    az account set --subscription $SubscriptionName
    
    # Verify subscription
    $currentSub = az account show --query name --output tsv
    Write-Host "Current subscription: $currentSub"
}

# Find PostgreSQL Flexible Servers based on criteria
Write-Host "Finding PostgreSQL Flexible Servers in resource group: $ResourceGroupName" -ForegroundColor Yellow
$allPostgreSQLServers = az resource list --resource-group $ResourceGroupName --resource-type "Microsoft.DBforPostgreSQL/flexibleServers" --query "[].{Name:name, Id:id, Tags:tags}" | ConvertFrom-Json

if ($TagName -and $TagValue) {
    Write-Host "Filtering by tag: $TagName = $TagValue" -ForegroundColor Yellow
    $postgreSQLServers = $allPostgreSQLServers | Where-Object { $_.Tags.$TagName -eq $TagValue }
} else {
    Write-Host "No tags specified - using ALL PostgreSQL Flexible Servers" -ForegroundColor Yellow
    $postgreSQLServers = $allPostgreSQLServers
}

# Check if any PostgreSQL servers were found
if (-not $postgreSQLServers -or $postgreSQLServers.Count -eq 0) {
    Write-Host "No PostgreSQL Flexible Servers found matching criteria" -ForegroundColor Red
    if ($TagName -and $TagValue) {
        Write-Host "Try running without tags to see all PostgreSQL servers in the resource group" -ForegroundColor Cyan
    }
    exit 1
}

Write-Host "Found $($postgreSQLServers.Count) PostgreSQL Flexible Servers:" -ForegroundColor Green
foreach ($server in $postgreSQLServers) {
    Write-Host "  $($server.Name)" -ForegroundColor Cyan
}

# Confirm before proceeding
Write-Host ""
$confirm = Read-Host "Assign $CustomRoleName role to these PostgreSQL servers? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Operation cancelled" -ForegroundColor Red
    exit 0
}

# Assign PostgreSQL Flexible Server Operator role to each server
Write-Host ""
Write-Host "Assigning roles..." -ForegroundColor Green

$successCount = 0
$errorCount = 0

foreach ($server in $postgreSQLServers) {
    try {
        Write-Host "  Assigning role to: $($server.Name)"
        
        az role assignment create --assignee $PrincipalId --role $CustomRoleName --scope $server.Id --output none
            
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
az role assignment list --assignee $PrincipalId --query "[?roleDefinitionName=='$CustomRoleName'].{PrincipalId:principalId, Role:roleDefinitionName, Scope:scope}" --output table

Write-Host ""
Write-Host "Role assignment completed!" -ForegroundColor Green
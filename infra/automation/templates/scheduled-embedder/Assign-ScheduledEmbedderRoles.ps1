# Tag-based ScheduledEmbedder Role Assignment Script
# Assigns Virtual Machine Contributor role to VMs and PostgreSQL Flexible Server Operator role to PostgreSQL servers with specific tags (optional)

param(
    [Parameter(Mandatory=$true)]
    [string]$PrincipalId,
    
    [string]$VMResourceGroupName = "rg-myproject-vms",
    [string]$PostgreSQLResourceGroupName = "rg-myproject-apps", 
    [string]$SubscriptionName = "",
    [string]$VMTagName = "",
    [string]$VMTagValue = "",
    [string]$PostgreSQLTagName = "",
    [string]$PostgreSQLTagValue = "",
    [string]$EnvironmentSuffix = "Dev",
    [string]$PostgreSQLBaseRoleName = "PostgreSQL Flexible Server Operator"
)

$PostgreSQLCustomRoleName = "$PostgreSQLBaseRoleName - $EnvironmentSuffix"
$VMRoleName = "Virtual Machine Contributor"

Write-Host "=== ScheduledEmbedder Role Assignment Script ===" -ForegroundColor Green
Write-Host "Virtual Machine role: $VMRoleName" -ForegroundColor Cyan
Write-Host "PostgreSQL custom role: $PostgreSQLCustomRoleName" -ForegroundColor Cyan

# Switch to the correct subscription if specified
if ($SubscriptionName) {
    Write-Host "Switching to subscription: $SubscriptionName"
    az account set --subscription $SubscriptionName
    
    # Verify subscription
    $currentSub = az account show --query name --output tsv
    Write-Host "Current subscription: $currentSub"
}

# Find Virtual Machines based on criteria
Write-Host "Finding Virtual Machines in resource group: $VMResourceGroupName" -ForegroundColor Yellow
$allVMs = az resource list --resource-group $VMResourceGroupName --resource-type "Microsoft.Compute/virtualMachines" --query "[].{Name:name, Id:id, Tags:tags}" | ConvertFrom-Json

if ($VMTagName -and $VMTagValue) {
    Write-Host "Filtering VMs by tag: $VMTagName = $VMTagValue" -ForegroundColor Yellow
    $virtualMachines = $allVMs | Where-Object { $_.Tags.$VMTagName -eq $VMTagValue }
} else {
    Write-Host "No VM tags specified - using ALL Virtual Machines" -ForegroundColor Yellow
    $virtualMachines = $allVMs
}

# Find PostgreSQL Flexible Servers based on criteria
Write-Host "Finding PostgreSQL Flexible Servers in resource group: $PostgreSQLResourceGroupName" -ForegroundColor Yellow
$allPostgreSQLServers = az resource list --resource-group $PostgreSQLResourceGroupName --resource-type "Microsoft.DBforPostgreSQL/flexibleServers" --query "[].{Name:name, Id:id, Tags:tags}" | ConvertFrom-Json

if ($PostgreSQLTagName -and $PostgreSQLTagValue) {
    Write-Host "Filtering PostgreSQL by tag: $PostgreSQLTagName = $PostgreSQLTagValue" -ForegroundColor Yellow
    $postgreSQLServers = $allPostgreSQLServers | Where-Object { $_.Tags.$PostgreSQLTagName -eq $PostgreSQLTagValue }
} else {
    Write-Host "No PostgreSQL tags specified - using ALL PostgreSQL Flexible Servers" -ForegroundColor Yellow
    $postgreSQLServers = $allPostgreSQLServers
}

# Check if any resources were found
$hasVMs = $virtualMachines -and $virtualMachines.Count -gt 0
$hasPostgreSQL = $postgreSQLServers -and $postgreSQLServers.Count -gt 0

if (-not $hasVMs -and -not $hasPostgreSQL) {
    Write-Host "No Virtual Machines or PostgreSQL Flexible Servers found matching criteria" -ForegroundColor Red
    if (($VMTagName -and $VMTagValue) -or ($PostgreSQLTagName -and $PostgreSQLTagValue)) {
        Write-Host "Try running without tags to see all resources in the resource groups" -ForegroundColor Cyan
    }
    exit 1
}

# Display found resources
if ($hasVMs) {
    Write-Host "Found $($virtualMachines.Count) Virtual Machines:" -ForegroundColor Green
    foreach ($vm in $virtualMachines) {
        Write-Host "  $($vm.Name)" -ForegroundColor Cyan
    }
}

if ($hasPostgreSQL) {
    Write-Host "Found $($postgreSQLServers.Count) PostgreSQL Flexible Servers:" -ForegroundColor Green
    foreach ($server in $postgreSQLServers) {
        Write-Host "  $($server.Name)" -ForegroundColor Cyan
    }
}

# Confirm before proceeding
Write-Host ""
$confirm = Read-Host "Assign roles to these resources? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Operation cancelled" -ForegroundColor Red
    exit 0
}

# Assign roles
Write-Host ""
Write-Host "Assigning roles..." -ForegroundColor Green

$successCount = 0
$errorCount = 0

# Assign Virtual Machine Contributor role to each VM
if ($hasVMs) {
    Write-Host "Assigning Virtual Machine Contributor role..." -ForegroundColor Yellow
    foreach ($vm in $virtualMachines) {
        try {
            Write-Host "  Assigning role to VM: $($vm.Name)"
            
            az role assignment create --assignee $PrincipalId --role $VMRoleName --scope $vm.Id --output none
                
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
}

# Assign PostgreSQL Flexible Server Operator role to each server
if ($hasPostgreSQL) {
    Write-Host "Assigning PostgreSQL Flexible Server Operator role..." -ForegroundColor Yellow
    foreach ($server in $postgreSQLServers) {
        try {
            Write-Host "  Assigning role to PostgreSQL: $($server.Name)"
            
            az role assignment create --assignee $PrincipalId --role $PostgreSQLCustomRoleName --scope $server.Id --output none
                
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
}

Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Green
Write-Host "Successful assignments: $successCount" -ForegroundColor Green
Write-Host "Failed assignments: $errorCount" -ForegroundColor $(if ($errorCount -eq 0) { "Green" } else { "Red" })

# Check for authentication issues
if ($errorCount -gt 0) {
    Write-Host ""
    Write-Host "💡 If you see Microsoft Graph authentication errors:" -ForegroundColor Cyan
    Write-Host "   1. az logout" -ForegroundColor Cyan
    Write-Host "   2. az login --scope https://graph.microsoft.com//.default" -ForegroundColor Cyan
    Write-Host "   3. az account set --subscription '$SubscriptionName'" -ForegroundColor Cyan
    Write-Host "   4. Re-run this script" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "💡 Make sure the custom PostgreSQL role exists in the subscription:" -ForegroundColor Cyan
    Write-Host "   Deploy the PostgreSQL custom role first if needed" -ForegroundColor Cyan
}
# Tag-based VM Role Assignment Script
# Assigns Virtual Machine Contributor role to VMs with specific tags (optional)

param(
    [Parameter(Mandatory=$true)]
    [string]$PrincipalId,
    
    [string]$ResourceGroupName = "rg-myproject-vms",
    [string]$SubscriptionName = "",
    [string]$TagName = "",
    [string]$TagValue = ""
)

$VMRoleName = "Virtual Machine Contributor"

Write-Host "=== VM Role Assignment Script ===" -ForegroundColor Green
Write-Host "Virtual Machine role: $VMRoleName" -ForegroundColor Cyan

# Switch to the correct subscription if specified
if ($SubscriptionName) {
    Write-Host "Switching to subscription: $SubscriptionName"
    az account set --subscription $SubscriptionName
    
    # Verify subscription
    $currentSub = az account show --query name --output tsv
    Write-Host "Current subscription: $currentSub"
}

# Find Virtual Machines based on criteria
Write-Host "Finding Virtual Machines in resource group: $ResourceGroupName" -ForegroundColor Yellow
$allVMs = az resource list --resource-group $ResourceGroupName --resource-type "Microsoft.Compute/virtualMachines" --query "[].{Name:name, Id:id, Tags:tags}" | ConvertFrom-Json

if ($TagName -and $TagValue) {
    Write-Host "Filtering VMs by tag: $TagName = $TagValue" -ForegroundColor Yellow
    $virtualMachines = $allVMs | Where-Object { $_.Tags.$TagName -eq $TagValue }
} else {
    Write-Host "No tags specified - using ALL Virtual Machines" -ForegroundColor Yellow
    $virtualMachines = $allVMs
}

# Check if any VMs were found
if (-not $virtualMachines -or $virtualMachines.Count -eq 0) {
    Write-Host "No Virtual Machines found matching criteria" -ForegroundColor Red
    if ($TagName -and $TagValue) {
        Write-Host "Try running without tags to see all VMs in the resource group" -ForegroundColor Cyan
    }
    exit 1
}

Write-Host "Found $($virtualMachines.Count) Virtual Machines:" -ForegroundColor Green
foreach ($vm in $virtualMachines) {
    Write-Host "  $($vm.Name)" -ForegroundColor Cyan
}

# Confirm before proceeding
Write-Host ""
$confirm = Read-Host "Assign $VMRoleName role to these VMs? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Operation cancelled" -ForegroundColor Red
    exit 0
}

# Assign Virtual Machine Contributor role to each VM
Write-Host ""
Write-Host "Assigning roles..." -ForegroundColor Green

$successCount = 0
$errorCount = 0

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
}
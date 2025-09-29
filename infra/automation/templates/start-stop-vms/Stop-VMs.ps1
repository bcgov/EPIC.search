param(
    [string]$SubscriptionId,
    [string]$ResourceGroupName,
    [string]$VMNames
)

# Output the parameters
Write-Output "Subscription ID: $SubscriptionId"
Write-Output "Resource Group Name: $ResourceGroupName"
Write-Output "VM Names: $VMNames"

# Connect to Azure using managed identity
Connect-AzAccount -Identity

# Set the subscription context dynamically
Set-AzContext -SubscriptionId $SubscriptionId

# Split the VMNames parameter into an array
$VMNameArray = $VMNames -split ',' | ForEach-Object { $_.Trim() }

Write-Output "Processing $($VMNameArray.Count) VM(s) for shutdown..."

# Stop VMs
foreach ($VMName in $VMNameArray) {
    if ([string]::IsNullOrWhiteSpace($VMName)) {
        continue
    }
    
    try {
        Write-Output "Stopping VM: $VMName in resource group: $ResourceGroupName"
        
        # Check if VM exists
        $vm = Get-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName -ErrorAction SilentlyContinue
        if (-not $vm) {
            Write-Warning "VM '$VMName' not found in resource group '$ResourceGroupName'"
            continue
        }
        
        # Check current power state
        $vmStatus = Get-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName -Status
        $powerState = ($vmStatus.Statuses | Where-Object {$_.Code -like "PowerState/*"}).Code
        
        if ($powerState -eq "PowerState/deallocated") {
            Write-Output "VM '$VMName' is already deallocated"
        } elseif ($powerState -eq "PowerState/deallocating") {
            Write-Output "VM '$VMName' is already deallocating"
        } else {
            Stop-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName -Force -NoWait
            Write-Output "Stopped VM: $VMName (async)"
        }
    }
    catch {
        Write-Error "Failed to stop VM '$VMName': $($_.Exception.Message)"
    }
}

Write-Output "VM shutdown commands completed."
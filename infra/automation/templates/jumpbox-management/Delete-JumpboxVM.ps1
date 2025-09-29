# Delete-JumpboxVM.ps1
#
# This script removes a jumpbox VM and its associated resources to save costs.

param(
    [Parameter(Mandatory = $true)]
    [string]$SubscriptionId,
    
    [Parameter(Mandatory = $true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory = $false)]
    [string]$VMName = "vm-jumpbox"
)

try {
    # Connect using managed identity
    Write-Output "Connecting to Azure using managed identity..."
    Connect-AzAccount -Identity

    # Set subscription context
    Write-Output "Setting subscription context to: $SubscriptionId"
    Set-AzContext -SubscriptionId $SubscriptionId

    # Get VM
    Write-Output "Looking for VM '$VMName' in resource group '$ResourceGroupName'..."
    $vm = Get-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName
    if (-not $vm) {
        Write-Warning "VM $VMName not found in resource group $ResourceGroupName"
        return
    }

    # Get associated resources
    Write-Output "Getting associated resources..."
    $nics = $vm.NetworkProfile.NetworkInterfaces
    $osDisk = $vm.StorageProfile.OSDisk

    # Delete VM
    Write-Output "Removing VM $VMName..."
    Remove-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName -Force

    # Delete NICs
    foreach ($nic in $nics) {
        $nicId = $nic.Id
        $nicName = $nicId.Split('/')[-1]
        Write-Output "Removing NIC $nicName..."
        Remove-AzNetworkInterface -ResourceGroupName $ResourceGroupName -Name $nicName -Force
    }

    # Delete OS disk
    $diskName = $osDisk.Name
    Write-Output "Removing OS disk $diskName..."
    Remove-AzDisk -ResourceGroupName $ResourceGroupName -DiskName $diskName -Force

    Write-Output "VM $VMName and associated resources have been removed successfully!"

} catch { 
    Write-Error "Failed to remove VM: $_"
    throw
}
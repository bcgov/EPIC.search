# Deploy-JumpboxVM.ps1
#
# This script deploys a jumpbox VM for troubleshooting purposes.
# The VM is deployed to a specified subnet and configured for Bastion access.

param(
    [Parameter(Mandatory = $true)]
    [string]$SubscriptionId,
    
    [Parameter(Mandatory = $true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory = $true)]
    [string]$Location,
    
    [Parameter(Mandatory = $true)]
    [string]$VNetName,
    
    [Parameter(Mandatory = $true)]
    [string]$VNetResourceGroupName,
    
    [Parameter(Mandatory = $true)]
    [string]$SubnetName,
    
    [Parameter(Mandatory = $false)]
    [string]$VMName = "vm-jumpbox",
    
    [Parameter(Mandatory = $false)]
    [string]$VMSize = "Standard_D4s_v3", # 4 vCPUs, 16 GB RAM - good for troubleshooting tools
    
    [Parameter(Mandatory = $false)]
    [string]$AdminUsername = "jumpadmin",
    
    [Parameter(Mandatory = $false)]
    [ValidateSet("Windows", "Linux")]
    [string]$OSType = "Windows",
    
    [Parameter(Mandatory = $true)]
    [object]$AdminPasswordOrKey
)

# Convert string password to SecureString if needed
if ($AdminPasswordOrKey -is [string]) {
    $AdminPasswordOrKey = ConvertTo-SecureString -String $AdminPasswordOrKey -AsPlainText -Force
}

# Ensure Az module is installed
if (-not (Get-Module -ListAvailable -Name Az.Compute)) {
    Write-Error "Az.Compute module is required. Install it using: Install-Module -Name Az.Compute -Force"
    exit 1
}

try {
    # Connect using managed identity
    Write-Output "Connecting to Azure using managed identity..."
    Connect-AzAccount -Identity

    # Set subscription context
    Write-Output "Setting subscription context to: $SubscriptionId"
    Set-AzContext -SubscriptionId $SubscriptionId

    # Get Virtual Network from its resource group
    Write-Output "Getting VNet '$VNetName' from resource group '$VNetResourceGroupName'..."
    $vnet = Get-AzVirtualNetwork -Name $VNetName -ResourceGroupName $VNetResourceGroupName
    if (-not $vnet) {
        throw "VNet $VNetName not found in resource group $VNetResourceGroupName"
    }

    # Get subnet reference
    Write-Output "Looking for subnet '$SubnetName' in VNet '$VNetName'..."
    $subnet = $vnet.Subnets | Where-Object { $_.Name -eq $SubnetName }
    
    if (-not $subnet) {
        Write-Output "Available subnets in VNet '$VNetName':"
        $vnet.Subnets | ForEach-Object { Write-Output "- $($_.Name)" }
        throw "Subnet $SubnetName not found in VNet $VNetName"
    }

    # Create NIC in the VM's resource group
    $nicName = "$VMName-nic"
    Write-Output "Creating network interface '$nicName'..."
    $nic = New-AzNetworkInterface -Name $nicName -ResourceGroupName $ResourceGroupName -Location $Location -SubnetId $subnet.Id -Force

    # VM Configuration
    Write-Output "Creating VM configuration..."
    $VMConfig = New-AzVMConfig -VMName $VMName -VMSize $VMSize

    if ($OSType -eq "Windows") {
        # Windows Server 2022 - good balance of modern features and stability
        $VMConfig = Set-AzVMOperatingSystem -VM $VMConfig -Windows -ComputerName $VMName -Credential (New-Object PSCredential ($AdminUsername, $AdminPasswordOrKey))
        $VMConfig = Set-AzVMSourceImage -VM $VMConfig -PublisherName "MicrosoftWindowsServer" -Offer "WindowsServer" -Skus "2022-datacenter-g2" -Version "latest"
    }
    else {
        # Ubuntu 22.04 LTS - good for networking tools and troubleshooting
        $VMConfig = Set-AzVMOperatingSystem -VM $VMConfig -Linux -ComputerName $VMName -Credential (New-Object PSCredential ($AdminUsername, $AdminPasswordOrKey))
        $VMConfig = Set-AzVMSourceImage -VM $VMConfig -PublisherName "Canonical" -Offer "0001-com-ubuntu-server-jammy" -Skus "22_04-lts-gen2" -Version "latest"
    }

    # Add NIC
    $VMConfig = Add-AzVMNetworkInterface -VM $VMConfig -Id $nic.Id
    
    # Configure boot diagnostics
    $VMConfig = Set-AzVMBootDiagnostic -VM $VMConfig -Disable

    # Create the VM
    Write-Output "Creating VM $VMName..."
    New-AzVM -ResourceGroupName $ResourceGroupName -Location $Location -VM $VMConfig

    # Tags for cost tracking and automation
    $tags = @{
        "Purpose" = "Troubleshooting"
        "AutoShutdown" = "True"
        "Environment" = $ResourceGroupName.Split('-')[-1] # Assuming RG follows naming convention rg-xxx-env
        "CreatedBy" = "JumpboxAutomation"
        "CreatedDate" = (Get-Date).ToString("yyyy-MM-dd")
    }

    Update-AzTag -ResourceId (Get-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName).Id -Tag $tags -Operation Merge

    Write-Host "VM $VMName has been deployed successfully!"
    Write-Host "Connect to this VM using Azure Bastion"

} catch {
    Write-Error "Failed to deploy VM: $_"
    throw
}
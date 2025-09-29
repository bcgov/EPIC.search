# Jumpbox Management Scripts

This directory contains PowerShell scripts for deploying and managing temporary jumpbox VMs for troubleshooting purposes. These VMs are designed for on-demand deployment when network troubleshooting or secure access to internal resources is required.

## Files Overview

- **`Deploy-JumpboxVM.ps1`** - Deploys a jumpbox VM with proper network configuration and tagging
- **`Delete-JumpboxVM.ps1`** - Removes the jumpbox VM and all associated resources to save costs

## Use Cases

- **Network Troubleshooting**: Deploy when you need to diagnose network connectivity issues
- **Secure Access**: Temporary access to internal resources via Bastion
- **Testing**: Validate configurations or test connectivity from within the network
- **Emergency Access**: Quick deployment for urgent troubleshooting scenarios

## Deploy-JumpboxVM.ps1

### Deploy Script Required Parameters

- **SubscriptionId** - Azure subscription ID where the VM will be deployed
- **ResourceGroupName** - Resource group for the jumpbox VM resources
- **Location** - Azure region for deployment (e.g., "Canada Central")
- **VNetName** - Name of the existing Virtual Network
- **VNetResourceGroupName** - Resource group containing the VNet (can be different from VM resource group)
- **SubnetName** - Name of the subnet where the VM will be deployed
- **AdminPasswordOrKey** - Password or SSH key for the VM administrator account

### Deploy Script Optional Parameters

- **VMName** - Default: "vm-jumpbox" (customize if you need multiple jumpboxes)
- **VMSize** - Default: "Standard_D4s_v3" (4 vCPUs, 16 GB RAM)
- **AdminUsername** - Default: "jumpadmin"
- **OSType** - Default: "Windows" (options: "Windows" or "Linux")

### OS Options

- **Windows**: Windows Server 2022 Datacenter - includes RDP, PowerShell, network troubleshooting tools
- **Linux**: Ubuntu 22.04 LTS - includes SSH, network utilities, debugging tools

### Automatic Tagging

The script applies these tags for tracking and automation:

- **Purpose**: "Troubleshooting"
- **AutoShutdown**: "True" (for potential automated cleanup)
- **Environment**: Derived from resource group name
- **CreatedBy**: "JumpboxAutomation"
- **CreatedDate**: Current date

### Deploy Script Usage Examples

```powershell
# Deploy Windows jumpbox
.\Deploy-JumpboxVM.ps1 `
    -SubscriptionId "12345678-1234-1234-1234-123456789012" `
    -ResourceGroupName "rg-myproject-troubleshooting" `
    -Location "Canada Central" `
    -VNetName "vnet-myproject-main" `
    -VNetResourceGroupName "rg-myproject-network" `
    -SubnetName "snet-internal" `
    -AdminPasswordOrKey (Read-Host -AsSecureString "Enter admin password")

# Deploy Linux jumpbox with custom name
.\Deploy-JumpboxVM.ps1 `
    -SubscriptionId "12345678-1234-1234-1234-123456789012" `
    -ResourceGroupName "rg-myproject-troubleshooting" `
    -Location "Canada Central" `
    -VNetName "vnet-myproject-main" `
    -VNetResourceGroupName "rg-myproject-network" `
    -SubnetName "snet-internal" `
    -VMName "vm-jumpbox-dev" `
    -OSType "Linux" `
    -AdminPasswordOrKey (Read-Host -AsSecureString "Enter admin password")
```

## Delete-JumpboxVM.ps1

### Delete Script Required Parameters

- **SubscriptionId** - Azure subscription ID containing the VM
- **ResourceGroupName** - Resource group containing the jumpbox VM

### Delete Script Optional Parameters

- **VMName** - Default: "vm-jumpbox" (must match the VM name you want to delete)

### What Gets Deleted

The script performs complete cleanup of:

1. **Virtual Machine** - The jumpbox VM itself
2. **Network Interface(s)** - All NICs associated with the VM
3. **OS Disk** - The managed disk used by the VM

### Delete Script Usage Examples

```powershell
# Delete default jumpbox
.\Delete-JumpboxVM.ps1 `
    -SubscriptionId "12345678-1234-1234-1234-123456789012" `
    -ResourceGroupName "rg-myproject-troubleshooting"

# Delete custom-named jumpbox
.\Delete-JumpboxVM.ps1 `
    -SubscriptionId "12345678-1234-1234-1234-123456789012" `
    -ResourceGroupName "rg-myproject-troubleshooting" `
    -VMName "vm-jumpbox-dev"
```

## Required Permissions

The managed identity or user account running these scripts needs:

### For Deployment (Deploy-JumpboxVM.ps1)

- **Virtual Machine Contributor** role on the target resource group
- **Network Contributor** role on the VNet resource group
- **Reader** role on the subscription (for context switching)

### For Deletion (Delete-JumpboxVM.ps1)

- **Virtual Machine Contributor** role on the resource group containing the VM
- **Storage Account Contributor** role (for managed disk deletion)

## Security Considerations

- **Temporary Nature**: These VMs should be short-lived and deleted when troubleshooting is complete
- **Bastion Access**: VMs are designed for access via Azure Bastion, not direct public IP
- **Cost Control**: Use the AutoShutdown tag to implement automated cost controls
- **Monitoring**: Track creation/deletion via the applied tags

## Future Automation Potential

These scripts are structured to be easily converted into Azure Automation runbooks if you decide to automate jumpbox lifecycle management:

- **Scheduled Deployment**: Deploy jumpboxes on a schedule for regular testing
- **Auto-Cleanup**: Automatically delete jumpboxes after a certain time period
- **Event-Driven**: Deploy in response to monitoring alerts or service desk requests
- **Self-Service**: Allow teams to request jumpboxes through automation workflows

## Best Practices

1. **Always delete jumpboxes** when troubleshooting is complete to avoid unnecessary costs
2. **Use appropriate VM sizing** - Standard_D4s_v3 is good for most troubleshooting, scale up/down as needed
3. **Tag consistently** - The automatic tagging helps with cost tracking and governance
4. **Document usage** - Keep track of when and why jumpboxes were deployed
5. **Security compliance** - Ensure jumpboxes comply with your organization's security policies

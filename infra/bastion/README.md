# Azure Bastion Infrastructure Templates

This folder contains Bicep templates for deploying Azure Bastion with its required network security group.

## Files Overview

- **`main.bicep`** - Main template that orchestrates the entire Bastion deployment
- **`bastion.bicep`** - Core Bastion Host template with Public IP and subnet creation
- **`nsg.bicep`** - Network Security Group template with Bastion-specific rules
- **`subnet.bicep`** - Helper template for creating subnets across resource groups
- **`main.bicepparam`** - Sample parameters file

## Architecture

The templates deploy:

1. **Network Security Group** - Pre-configured with Azure Bastion required rules:
   - HTTPS inbound (443) from Internet
   - GatewayManager inbound (443)
   - Bastion Host Communication inbound (4443)
   - Load Balancer inbound (443)
   - SSH/RDP outbound (22/3389) to VirtualNetwork
   - Azure Cloud outbound (443)
   - Bastion Communication outbound (8080/5701)
   - HTTP outbound (80) to Internet

2. **AzureBastionSubnet** - The required subnet (name cannot be changed)
   - Minimum /26 address space required
   - NSG applied automatically

3. **Public IP Address** - Standard SKU with static allocation
   - DNS label auto-generated with unique suffix

4. **Azure Bastion Host** - The Bastion service itself
   - Configurable SKU (Basic, Standard, Developer, Premium)
   - Minimum 2 scale units for Basic SKU

## Parameters

### Required Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `bastionName` | Name of the Azure Bastion resource | `bastion-myproject` |
| `vnetName` | Name of the existing virtual network | `vnet-myproject` |
| `bastionSubnetAddressPrefix` | Address prefix for AzureBastionSubnet | `10.0.1.0/26` |

### Optional Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `vnetResourceGroupName` | Current RG | Resource group where VNet exists |
| `location` | Current RG location | Azure region for resources |
| `bastionSku` | `Basic` | Bastion SKU (Basic/Standard/Developer/Premium) |
| `bastionNsgName` | `nsg-bastion` | Name for the Bastion NSG |
| `tags` | Default tags | Resource tags |

## Deployment

### Using Azure CLI

```bash
# Deploy with parameters file
az deployment group create \
  --resource-group rg-myproject-bastion \
  --template-file main.bicep \
  --parameters main.bicepparam

# Deploy with inline parameters
az deployment group create \
  --resource-group rg-myproject-bastion \
  --template-file main.bicep \
  --parameters \
    bastionName=bastion-myproject \
    vnetName=vnet-myproject \
    bastionSubnetAddressPrefix=10.0.1.0/26
```

### Using Azure PowerShell

```powershell
# Deploy with parameters file
New-AzResourceGroupDeployment `
  -ResourceGroupName "rg-myproject-bastion" `
  -TemplateFile "main.bicep" `
  -TemplateParameterFile "main.bicepparam"

# Deploy with inline parameters
New-AzResourceGroupDeployment `
  -ResourceGroupName "rg-myproject-bastion" `
  -TemplateFile "main.bicep" `
  -bastionName "bastion-myproject" `
  -vnetName "vnet-myproject" `
  -bastionSubnetAddressPrefix "10.0.1.0/26"
```

## Cross-Resource Group Deployment

If your VNet is in a different resource group:

1. Deploy the main template to the resource group where you want Bastion resources
2. Set the `vnetResourceGroupName` parameter to point to the VNet's resource group
3. Ensure you have appropriate permissions on both resource groups

## Prerequisites

1. **Existing Virtual Network** - The VNet must already exist
2. **Available Address Space** - At least /26 subnet space available
3. **Permissions** - Contributor access to target resource group(s)
4. **Unique Bastion Name** - Must be unique within the region

## Outputs

| Output | Description |
|--------|-------------|
| `bastionId` | Resource ID of the Bastion Host |
| `bastionName` | Name of the deployed Bastion Host |
| `bastionFqdn` | FQDN for the Bastion endpoint |
| `bastionPublicIpAddress` | Public IP address of Bastion |
| `bastionSubnetId` | Resource ID of the AzureBastionSubnet |

## Best Practices

1. **Subnet Sizing** - Use /26 for Basic SKU, consider /24 for higher SKUs
2. **Naming Convention** - Follow organizational naming standards
3. **Tagging** - Update the default tags to match your environment
4. **SKU Selection** - Start with Basic, upgrade based on feature needs
5. **Security** - Review NSG rules and adjust if additional restrictions needed

## Common Issues

1. **Subnet Name** - AzureBastionSubnet name is fixed and cannot be changed
2. **Subnet Size** - Must be /26 or larger (/25, /24, etc.)
3. **Public IP SKU** - Must be Standard SKU for Bastion
4. **Cross-RG Permissions** - Ensure permissions on both source and target RGs

## Optional Features

Uncomment in `bastion.bicep` to enable advanced features:

- `disableCopyPaste` - Disable copy/paste functionality
- `enableFileCopy` - Enable file transfer (Standard+ SKU)
- `enableIpConnect` - Enable IP-based connections (Standard+ SKU)  
- `enableKerberos` - Enable Kerberos authentication
- `enableSessionRecording` - Enable session recording (Premium SKU)
- `enableShareableLink` - Enable shareable links (Standard+ SKU)
- `enableTunneling` - Enable native client tunneling (Standard+ SKU)

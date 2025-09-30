# Bastion Deployment

## Quick Start

### 1. Copy and customize parameters

```powershell
# Copy the example file
Copy-Item "deploy-bastion.example.json" "deploy-bastion.dev.json"

# Edit deploy-bastion.dev.json with your values:
# - bastionResourceGroupName: Resource group for bastion resources (creates if not exists)
# - vnetName: Your existing VNet name
# - vnetResourceGroupName: Resource group where VNet exists
# - bastionSubnetAddressPrefix: /26 subnet within your VNet address space
```

### 2. Deploy Bastion

```powershell
az deployment sub create \
  --location "Canada Central" \
  --template-file "deploy-bastion.bicep" \
  --parameters "@deploy-bastion.dev.json"
```

**Note:** The template automatically creates the resource group if it doesn't exist, or deploys into it if it does exist (idempotent).

## Important Notes

### Subnet Requirements

- **Address Space:** Bastion subnet requires `/26` minimum (64 addresses)
- **Name:** Must be exactly `AzureBastionSubnet`
- **Location:** Must be within your existing VNet address space

### Find Available Address Space

```powershell
# Check VNet address space
az network vnet show --name "your-vnet-name" --resource-group "your-vnet-rg" \
  --query "addressSpace.addressPrefixes" --output table

# Check existing subnets
az network vnet subnet list --vnet-name "your-vnet-name" --resource-group "your-vnet-rg" \
  --query "[].{Name:name, AddressPrefix:addressPrefix}" --output table
```

## Files

- `deploy-bastion.bicep` - Main deployment template (creates RG if needed, then deploys bastion)
- `deploy-bastion.example.json` - Parameter template (commit to git)
- `deploy-bastion.dev.json` - Your environment values (excluded from git)

## Environment Files

Create separate parameter files for each environment:

- `deploy-bastion.dev.json`
- `deploy-bastion.test.json`
- `deploy-bastion.prod.json`

These files are excluded from git via `.gitignore`.
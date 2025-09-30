# Subnet Deployment

## Quick Start

### 1. Copy and customize parameters

```powershell
# Copy the example file
Copy-Item "deploy-all-subnets.example.json" "deploy-all-subnets.dev.json"

# Edit deploy-all-subnets.dev.json with your values:
# - vnetSubscriptionId: Your VNet subscription ID
# - vnetResourceGroupName: VNet resource group name
# - vnetName: Existing VNet name
# - Subnet address prefixes (10.X.X.X/XX format)
```

### 2. Deploy Subnets

**Note:** Subnets are typically deployed as part of the complete networking stack via `../deploy-complete-networking.bicep`. For standalone subnet deployment:

```powershell
az deployment group create \
  --resource-group "your-networking-rg" \
  --template-file "deploy-all-subnets.bicep" \
  --parameters "@deploy-all-subnets.dev.json"
```

## Files

- `deploy-all-subnets.bicep` - Main subnets template
- `deploy-all-subnets.example.json` - Parameter template (commit to git)
- `deploy-all-subnets.dev.json` - Your environment values (excluded from git)

## Environment Files

Create separate parameter files for each environment:

- `deploy-all-subnets.dev.json`
- `deploy-all-subnets.test.json`
- `deploy-all-subnets.prod.json`

These files are excluded from git via `.gitignore`.
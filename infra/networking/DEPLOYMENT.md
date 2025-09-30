# Complete Networking Stack Deployment

## Quick Start

### 1. Copy and customize parameters

```powershell
# Copy the example file
Copy-Item "deploy-complete-networking.example.json" "deploy-complete-networking.dev.json"

# Edit deploy-complete-networking.dev.json with your values:
# - environmentSuffix: "dev" (or "test", "prod")
# - vnetSubscriptionId: Your VNet subscription ID
# - vnetResourceGroupName: VNet resource group name  
# - vnetName: Existing VNet name
# - Subnet address prefixes (10.X.X.X/XX format)
```

### 2. Deploy Complete Stack

```powershell
az deployment sub create \
  --location "Canada Central" \
  --template-file "deploy-complete-networking.bicep" \
  --parameters "@deploy-complete-networking.dev.json"
```

## What This Deploys

1. **Network Security Groups (NSGs)** - All required NSGs for the environment
2. **Subnets** - All subnets with NSG associations and private endpoint policies

## Alternative: Component-Level Deployment

You can also deploy NSGs and subnets independently:

- **NSGs only**: See `nsg/DEPLOYMENT.md`  
- **Subnets only**: See `subnets/DEPLOYMENT.md`

## Files

- `deploy-complete-networking.bicep` - Main orchestration template
- `deploy-complete-networking.example.json` - Parameter template (commit to git)
- `deploy-complete-networking.dev.json` - Your environment values (excluded from git)

## Environment Files

Create separate parameter files for each environment:

- `deploy-complete-networking.dev.json`
- `deploy-complete-networking.test.json`
- `deploy-complete-networking.prod.json`

These files are excluded from git via `.gitignore`.
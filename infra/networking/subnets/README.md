# Subnet Templates

This directory contains Bicep templates for deploying subnets within existing VNets managed by the infrastructure team.

## Templates Overview

### Individual Subnet Templates (`templates/`)

- **`app-services-subnet.bicep`** - Subnet for Azure App Services with VNet integration
- **`postgresql-subnet.bicep`** - Subnet for Azure Database for PostgreSQL Flexible Server  
- **`private-endpoints-subnet.bicep`** - Subnet for private endpoints (storage, key vault, etc.)
- **`vms-subnet.bicep`** - Subnet for virtual machines and compute resources
- **`subnet-deployment.bicep`** - Helper module for cross-scope subnet deployment

### Orchestration Template

- **`deploy-all-subnets.bicep`** - Deploys all subnet types with conditional deployment

## Subnet Specifications

| Subnet Type | NSG Association | Delegations | Service Endpoints |
|-------------|----------------|-------------|-------------------|
| **App Services** | `nsg-app-services-{env}` | `Microsoft.Web/serverFarms` | Storage, KeyVault |
| **PostgreSQL** | `nsg-postgresql-{env}` | `Microsoft.DBforPostgreSQL/flexibleServers` | Storage |
| **Private Endpoints** | `nsg-private-endpoints-{env}` | None | Storage, KeyVault |
| **VMs** | `nsg-vms-{env}` | None | Storage, KeyVault |

## Prerequisites

1. **Resource Group** - Must be created first using `../deploy-resource-group.bicep`
2. **NSGs** - Must be deployed first using `../nsg/deploy-all-nsgs.bicep`
3. **Existing VNet** - Infrastructure team provides VNet details:
   - VNet subscription ID
   - VNet resource group name  
   - VNet name
   - Available address prefixes for subnets

## Deployment

### Step 1: Update Parameters

Edit `deploy-all-subnets.dev.bicepparam.json` with your environment values:

```json
{
  "vnetSubscriptionId": {
    "value": "your-actual-vnet-subscription-id"
  },
  "vnetResourceGroupName": {
    "value": "rg-networking-spoke-dev"
  },
  "vnetName": {
    "value": "vnet-epic-search-dev"
  },
  "appServicesSubnetAddressPrefix": {
    "value": "10.0.1.0/24"
  }
}
```

### Step 2: Deploy All Subnets

```powershell
# Navigate to subnets directory
cd subnets

# Deploy all subnets
az deployment group create `
  --resource-group "rg-epic-search-network-dev" `
  --name "subnets-dev-deployment-$(Get-Date -Format 'yyyyMMdd-HHmmss')" `
  --template-file deploy-all-subnets.bicep `
  --parameters "@deploy-all-subnets.dev.bicepparam.json" `
  --verbose
```

### Step 3: Verify Deployment

```powershell
# List all subnets in the VNet
az network vnet subnet list `
  --vnet-name "vnet-epic-search-dev" `
  --resource-group "rg-networking-spoke-dev" `
  --output table
```

## Conditional Deployment

You can selectively deploy subnets by setting the deployment flags in the parameter file:

```json
{
  "deployAppServicesSubnet": { "value": true },
  "deployPostgreSQLSubnet": { "value": false },
  "deployPrivateEndpointsSubnet": { "value": true },
  "deployVMsSubnet": { "value": false }
}
```

## Cross-Scope Architecture

The templates handle cross-scope deployment where:

- **NSGs** are in the networking resource group (`rg-epic-search-network-{env}`)
- **VNets** are in infrastructure-managed resource groups
- **Subnets** are deployed to the VNet resource group but reference NSGs from the networking resource group

## Integration with Services

Once subnets are deployed, they can be used by:

- **App Services** - VNet integration using the app services subnet
- **PostgreSQL** - Flexible server deployment in the PostgreSQL subnet
- **Private Endpoints** - Secure connectivity for storage, key vault, etc.
- **Virtual Machines** - Compute resources in the VMs subnet

## Next Steps

After subnet deployment:

1. Deploy Azure services that will use these subnets
2. Configure private endpoints for secure connectivity
3. Test network connectivity and security rules
4. Add specific NSG rules as needed for your applications

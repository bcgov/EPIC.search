# Network Security Groups (NSGs)

This directory contains Bicep templates for creating Network Security Groups required by organizational policy. Every subnet must be associated with an NSG for security compliance.

## NSG Templates

### Individual NSG Templates
- **`nsg-app-services.bicep`** - NSG for App Services subnets
- **`nsg-postgresql.bicep`** - NSG for PostgreSQL database subnets  
- **`nsg-private-endpoints.bicep`** - NSG for Private Endpoint subnets
- **`nsg-vms.bicep`** - NSG for Virtual Machine subnets

### Deployment Template
- **`deploy-all-nsgs.bicep`** - Deploy multiple NSGs together with consistent naming

## Features

### Shared Tags Integration
All NSGs use the shared tags function from `../../shared/tags.bicep`:
- Organizational tags (account_coding, billing_group, ministry_name)
- Component-specific tags (Component: 'NetworkSecurity')
- Purpose-specific tags (Purpose: service type)
- Environment tags for multi-environment deployments

### Consistent Naming
NSGs follow the naming convention: `nsg-{purpose}-{environment}`
- Example: `nsg-app-services-dev`, `nsg-postgresql-prod`

### Parameterized Deployment
- Environment-agnostic templates
- Customizable NSG names
- Optional deployment flags for selective NSG creation
- Location and tagging parameters

## Deployment Instructions

### Prerequisites
1. Update parameter file with your values:
   ```bash
   # Edit deploy-all-nsgs.dev.bicepparam.json
   # Update: accountCoding, billingGroup, ministryName
   ```

2. Set Azure subscription context:
   ```bash
   az account set --subscription "your-subscription-id"
   ```

### Deploy to Dev Environment (Testing)

#### Deploy All NSGs
```bash
cd infra/networking/nsg

az deployment group create \
  --resource-group "rg-your-dev-network" \
  --name "nsg-dev-deployment-$(date +%Y%m%d-%H%M%S)" \
  --template-file deploy-all-nsgs.bicep \
  --parameters @deploy-all-nsgs.dev.bicepparam.json \
  --verbose
```

#### Check Deployment Status
```bash
# List created NSGs
az network nsg list \
  --resource-group "rg-your-dev-network" \
  --query "[].{Name:name, Location:location, Rules:length(securityRules)}" \
  --output table

# Check specific NSG rules (to see defaults + policy additions)
az network nsg rule list \
  --resource-group "rg-your-dev-network" \
  --nsg-name "nsg-app-services-dev" \
  --output table

# Check applied tags
az network nsg show \
  --resource-group "rg-your-dev-network" \
  --name "nsg-app-services-dev" \
  --query "tags"
```

#### Teardown Test Environment
```bash
# List dev NSGs before deletion
az network nsg list \
  --resource-group "rg-your-dev-network" \
  --query "[?contains(name, '-dev')].name" \
  --output table

# Delete all dev NSGs
az network nsg list \
  --resource-group "rg-your-dev-network" \
  --query "[?contains(name, '-dev')].name" \
  --output tsv | xargs -I {} az network nsg delete \
  --resource-group "rg-your-dev-network" \
  --name {} \
  --no-wait
```

### Deploy Individual NSG (Alternative)
```bash
az deployment group create \
  --resource-group "rg-your-network" \
  --template-file nsg-app-services.bicep \
  --parameters \
    nsgName="nsg-app-services-prod" \
    accountCoding="your-account-code" \
    billingGroup="your-billing-group" \
    ministryName="Your Ministry"
```

### Deploy Specific NSGs Only
```bash
az deployment group create \
  --resource-group "rg-your-network" \
  --template-file deploy-all-nsgs.bicep \
  --parameters \
    environmentSuffix="prod" \
    deployAppServicesNSG=true \
    deployPostgreSQLNSG=true \
    deployPrivateEndpointsNSG=false \
    deployVMsNSG=false \
    accountCoding="your-account-code" \
    billingGroup="your-billing-group" \
    ministryName="Your Ministry"
```

## Security Rules

Currently, NSGs are deployed with empty security rules arrays. Security rules will be added based on:
- Organizational security policies
- Service-specific requirements
- Environment-specific access patterns

## Integration

These NSGs are designed to integrate with:
- **Subnet templates** (`../subnets/templates/`) - Automatic NSG association
- **Service deployments** - Security rules for specific services
- **Shared tags** - Consistent organizational tagging

## Next Steps

1. **Add security rules** - Based on your security rule templates
2. **Create parameter files** - For different environments
3. **Integrate with subnets** - Automatic NSG association in subnet templates
4. **Service-specific rules** - Add rules as services are deployed

## Compliance

All NSGs ensure compliance with organizational requirements:
- Policy-mandated NSG association with subnets
- Proper tagging for governance and cost tracking
- Consistent naming conventions
- Audit-ready configuration
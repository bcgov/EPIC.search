# Networking Infrastructure

This directory contains Bicep templates and configurations for managing networking infrastructure within existing landing zone VNets. The infrastructure team manages the hub VNet and spoke VNet creation/peering, while this automation handles NSGs, subnets, and service networking within those VNets.

## Architecture Overview

``` folder
Hub (Managed by Infra Team)
├── Dev VNet (Existing)
├── Test VNet (Existing) 
├── Prod VNet (Existing)
└── Tools VNet (Existing)
```

Our responsibility: NSGs → Subnets → Service Networking within existing VNets.

## Directory Structure

### **`nsg/`** - Network Security Groups

Foundation security layer - every subnet must have an NSG per policy.

- `base-nsg.bicep` - Default security rules compliant with organizational policy
- `web-tier-nsg.bicep` - Rules for web-facing services
- `app-tier-nsg.bicep` - Rules for application tiers
- `data-tier-nsg.bicep` - Rules for database and storage services
- `bastion-nsg.bicep` - Rules for Azure Bastion subnets

### **`subnets/`** - Subnet Management

Subnet creation within existing VNets using parameter-driven deployment.

#### **`templates/`** - Reusable subnet templates

- `web-subnet.bicep` - Web tier subnet template
- `app-subnet.bicep` - Application tier subnet template  
- `data-subnet.bicep` - Database tier subnet template
- `private-endpoint-subnet.bicep` - Private endpoint subnet template

#### Parameter-driven deployment

Subnets are deployed using subscription ID and VNet name parameters, allowing the same templates to work across all environments (dev/test/prod/tools) without environment-specific folders.

### **`services/`** - Service-Specific Networking

Networking configurations for specific Azure services.

- **`app-services/`** - App Service networking (VNet integration, private endpoints)
- **`postgresql/`** - PostgreSQL networking (private endpoints, firewall rules)
- **`storage/`** - Storage account networking (private endpoints, service endpoints)
- **`private-endpoints/`** - Private endpoint templates and configurations

### **`shared/`** - Shared Networking Components

- `networking-constants.bicep` - VNet names, CIDR ranges, common configurations
- `subnet-defaults.bicep` - Default subnet configurations and naming conventions

## Deployment Strategy

### Phase 0: Resource Group Setup

1. Create the networking resource group with proper tagging
2. Validate access and permissions

### Phase 1: NSG Foundation

1. Deploy base NSGs with policy-compliant rules
2. Create service-tier specific NSGs
3. Establish security baselines

### Phase 2: Subnet Creation

1. Deploy subnets into existing VNets using templates
2. Associate NSGs with subnets
3. Configure service endpoints where needed

### Phase 3: Service Integration

1. Configure service-specific networking
2. Deploy private endpoints for secure connectivity
3. Integrate with existing services (App Services, PostgreSQL, etc.)

## Getting Started

### Step 1: Create Resource Group

Before deploying any networking components, create the resource group:

```powershell
# Update parameter values in deploy-resource-group.dev.bicepparam.json first
az deployment sub create `
  --location "Canada Central" `
  --name "rg-networking-$(Get-Date -Format 'yyyyMMdd-HHmmss')" `
  --template-file deploy-resource-group.bicep `
  --parameters "@deploy-resource-group.dev.bicepparam.json" `
  --verbose
```

### Step 2: Deploy NSGs

Once the resource group exists, deploy the Network Security Groups:

```powershell
# Navigate to nsg directory
cd nsg

# Update parameter values in deploy-all-nsgs.dev.bicepparam.json first
az deployment group create `
  --resource-group "rg-epic-search-network-dev" `
  --name "nsg-dev-deployment-$(Get-Date -Format 'yyyyMMdd-HHmmss')" `
  --template-file deploy-all-nsgs.bicep `
  --parameters "@deploy-all-nsgs.dev.bicepparam.json" `
  --verbose
```

## Prerequisites

### Infrastructure Team Provided

- Hub VNet with gateway connectivity
- Spoke VNets (dev, test, prod, tools) with peering configured
- DNS zones and resolution
- Express Route or VPN connectivity (if applicable)

### Our Requirements

- Contributor access to spoke VNet resource groups
- Ability to create NSGs and subnets
- Network Contributor role for service networking

## Naming Conventions

Following organizational standards

- **NSGs**: `nsg-{purpose}-{environment}` (e.g., `nsg-web-dev`)
- **Subnets**: `snet-{service}-{environment}` (e.g., `snet-app-prod`)
- **Private Endpoints**: `pe-{service}-{environment}` (e.g., `pe-postgresql-prod`)

## Security Compliance

All networking resources must comply with organizational security policies:

- Every subnet requires an NSG
- Least-privilege access rules
- Audit logging enabled
- Proper tagging for governance

## Integration Points

This networking infrastructure integrates with

- **Automation** (`../automation/`) - Runbook networking requirements
- **Bastion** (`../bastion/`) - Secure access subnet requirements  
- **Shared Tags** (`../shared/`) - Consistent tagging across networking resources

## Next Steps

1. **Start with NSGs** - Foundation security layer
2. **Create subnet templates** - Reusable patterns
3. **Deploy environment-specific subnets** - Per landing zone requirements
4. **Integrate services** - Connect existing services to networking

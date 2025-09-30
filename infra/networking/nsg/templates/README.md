# NSG Templates

This folder contains individual Network Security Group (NSG) templates that can be used as standalone components or referenced by other templates.

## Templates

- `nsg-app-services.bicep` - App Services NSG template
- `nsg-postgresql.bicep` - PostgreSQL NSG template  
- `nsg-private-endpoints.bicep` - Private Endpoints NSG template
- `nsg-vms.bicep` - Virtual Machines NSG template

## Usage

These templates are designed to be used as modules in larger deployments or as standalone NSG definitions.

### As Modules

```bicep
module appServicesNSG 'templates/nsg-app-services.bicep' = {
  name: 'deploy-app-services-nsg'
  params: {
    nsgName: 'nsg-app-services-${environmentSuffix}'
    location: location
  }
}
```

### Standalone Deployment

```powershell
az deployment group create \
  --resource-group "your-rg" \
  --template-file "templates/nsg-app-services.bicep" \
  --parameters nsgName="nsg-app-services-dev" location="Canada Central"
```

## Structure

The main `deploy-all-nsgs.bicep` template uses direct resource definitions rather than these individual templates for simplicity, but these templates are maintained for modular use cases.
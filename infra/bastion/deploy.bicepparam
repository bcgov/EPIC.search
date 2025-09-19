using './deploy.bicep'

// Resource Group for Bastion resources
param bastionResourceGroupName = 'rg-myproject-bastion'

// Required Bastion parameters
param bastionName = 'bastion-myproject'
param vnetName = 'vnet-myproject'

// IMPORTANT: Bastion subnet must be within your VNet's address space and requires /26 (64 addresses) minimum
// To find available address space in your VNet, run:
// az network vnet show --name "your-vnet-name" --resource-group "your-vnet-rg" --query "addressSpace.addressPrefixes"
// az network vnet subnet list --vnet-name "your-vnet-name" --resource-group "your-vnet-rg" --query "[].{Name:name, AddressPrefix:addressPrefix}" --output table
param bastionSubnetAddressPrefix = '10.0.1.0/26'  // Example: Update to match your VNet address space

// VNet Resource Group (where your existing VNet is located)
param vnetResourceGroupName = 'rg-myproject-networking'

// Location for new resources
param location = 'Australia East'

// Optional parameters (uncomment and modify as needed)
// param bastionSku = 'Standard'  // Default is 'Developer' (free tier)
// param bastionNsgName = 'nsg-bastion-custom'

// Tags are provided automatically via policy, but can be overridden if needed
// param tags = {
//   Environment: 'dev'
//   Owner: 'your-team'
// }

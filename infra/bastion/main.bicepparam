using './main.bicep'

// Required parameters
param bastionName = 'bastion-myproject'
param vnetName = 'vnet-myproject'
param bastionSubnetAddressPrefix = '10.0.1.0/26'  // Update to match your VNet address space

// Optional parameters (uncomment and modify as needed)
// param vnetResourceGroupName = 'rg-myproject-networking'
// param location = 'Australia East'
// param bastionSku = 'Standard'  // Default is 'Developer' (free tier)
// param bastionNsgName = 'nsg-bastion-custom'

// Tags are provided automatically via policy, but can be overridden if needed
// param tags = {
//   Environment: 'dev'
//   Owner: 'your-team'
// }

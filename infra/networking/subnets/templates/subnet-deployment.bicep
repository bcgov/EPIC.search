// Helper module for deploying subnets to existing VNets
// This handles the cross-scope deployment to VNets managed by infrastructure team

@description('The name of the existing VNet')
param vnetName string

@description('The name of the subnet to create')
param subnetName string

@description('The address prefix for the subnet')
param subnetAddressPrefix string

@description('The resource ID of the NSG to associate with the subnet')
param networkSecurityGroupId string

@description('Service delegations for the subnet')
param delegations array = []

@description('Service endpoints for the subnet')
param serviceEndpoints array = []

@description('Optional route table ID for the subnet (temporary - will be removed in future)')
param routeTableId string = ''

// Reference the existing VNet
resource existingVNet 'Microsoft.Network/virtualNetworks@2024-01-01' existing = {
  name: vnetName
}

// Create the subnet
resource subnet 'Microsoft.Network/virtualNetworks/subnets@2024-01-01' = {
  parent: existingVNet
  name: subnetName
  properties: {
    addressPrefix: subnetAddressPrefix
    networkSecurityGroup: {
      id: networkSecurityGroupId
    }
    routeTable: !empty(routeTableId) ? {
      id: routeTableId
    } : null
    delegations: delegations
    serviceEndpoints: serviceEndpoints
    // Critical: Enable NSG rules for private endpoints
    privateEndpointNetworkPolicies: 'NetworkSecurityGroupEnabled'
    privateLinkServiceNetworkPolicies: 'Enabled'
  }
}

// Outputs
output subnetId string = subnet.id
output subnetName string = subnet.name
output subnetAddressPrefix string = subnet.properties.addressPrefix
output vnetName string = existingVNet.name
output vnetId string = existingVNet.id

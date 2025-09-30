// Private Endpoints Subnet Template
// Creates a subnet for private endpoints (storage, key vault, etc.)

@description('Environment suffix (e.g., dev, test, prod)')
param environmentSuffix string

@description('The subscription ID where the VNet is located')
param vnetSubscriptionId string

@description('The resource group name where the VNet is located')
param vnetResourceGroupName string

@description('The name of the existing VNet')
param vnetName string

@description('The address prefix for the private endpoints subnet (e.g., 10.0.3.0/24)')
param subnetAddressPrefix string

@description('Optional route table ID for the subnet (temporary - will be removed in future)')
param routeTableId string = ''

// Reference the NSG created for private endpoints
resource privateEndpointsNSG 'Microsoft.Network/networkSecurityGroups@2024-07-01' existing = {
  name: 'nsg-private-endpoints-${environmentSuffix}'
}

// Deploy subnet to the existing VNet using a module to handle cross-scope deployment
module subnetDeployment 'subnet-deployment.bicep' = {
  name: 'deploy-private-endpoints-subnet'
  scope: resourceGroup(vnetSubscriptionId, vnetResourceGroupName)
  params: {
    vnetName: vnetName
    subnetName: 'snet-private-endpoints-${environmentSuffix}'
    subnetAddressPrefix: subnetAddressPrefix
    networkSecurityGroupId: privateEndpointsNSG.id
    routeTableId: routeTableId
    delegations: [] // Private endpoints don't require delegations
    serviceEndpoints: [
      {
        service: 'Microsoft.Storage'
      }
      {
        service: 'Microsoft.KeyVault'
      }
    ]
  }
}

// Outputs
output subnetId string = subnetDeployment.outputs.subnetId
output subnetName string = subnetDeployment.outputs.subnetName
output subnetAddressPrefix string = subnetDeployment.outputs.subnetAddressPrefix
output nsgId string = privateEndpointsNSG.id
output vnetName string = subnetDeployment.outputs.vnetName
output vnetId string = subnetDeployment.outputs.vnetId

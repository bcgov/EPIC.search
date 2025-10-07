targetScope = 'subscription'

@description('Resource group for AI resources')
param resourceGroupName string

@description('Location for resources')
param location string

@description('Environment suffix (e.g., dev, test, prod)')
param environmentSuffix string

@description('Computer Vision account name')
param visionAccountName string

@description('VNet subscription id for private endpoints subnet')
param vnetSubscriptionId string

@description('VNet resource group')
param vnetResourceGroupName string

@description('VNet name')
param vnetName string

@description('Tags to apply')
param tags object = {}

var subnetName = 'snet-private-endpoints-${environmentSuffix}'

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module vision './modules/vision-account.bicep' = {
  scope: rg
  params: {
    location: location
    accountName: visionAccountName
    tags: tags
  }
}

resource existingVnet 'Microsoft.Network/virtualNetworks@2024-07-01' existing = {
  scope: resourceGroup(vnetSubscriptionId, vnetResourceGroupName)
  name: vnetName
}

resource privateEndpointsSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' existing = {
  name: subnetName
  parent: existingVnet
}

module pe './modules/private-endpoint.bicep' = {
  scope: rg
  params: {
    location: location
    peName: 'pe-${visionAccountName}'
    targetResourceId: vision.outputs.accountId
    subnetId: privateEndpointsSubnet.id
    groupIds: [ 'account' ]
  }
}

output visionAccountId string = vision.outputs.accountId
output visionEndpoint string = vision.outputs.endpoint
output privateEndpointId string = pe.outputs.privateEndpointId

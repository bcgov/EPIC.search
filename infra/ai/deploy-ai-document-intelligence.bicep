targetScope = 'subscription'

@description('Resource group for AI resources')
param resourceGroupName string

@description('Location for resources')
param location string

@description('Environment suffix (e.g., dev, test, prod)')
param environmentSuffix string

@description('Document Intelligence account name')
param docIntAccountName string

@description('VNet subscription id for private endpoints subnet')
param vnetSubscriptionId string

@description('VNet resource group')
param vnetResourceGroupName string

@description('VNet name')
param vnetName string

@description('Tags to apply')
param tags object = {}

@description('Location for Private Endpoints (should match VNet region)')
param privateEndpointLocation string = location

var subnetName = 'snet-private-endpoints-${environmentSuffix}'

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module di './modules/document-intelligence-account.bicep' = {
  scope: rg
  params: {
    location: location
    accountName: docIntAccountName
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
    location: privateEndpointLocation
    peName: 'pe-${docIntAccountName}'
    targetResourceId: di.outputs.accountId
    subnetId: privateEndpointsSubnet.id
    groupIds: [ 'account' ]
  }
}

output docIntAccountId string = di.outputs.accountId
output docIntEndpoint string = di.outputs.endpoint
output privateEndpointId string = pe.outputs.privateEndpointId

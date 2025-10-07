targetScope = 'subscription'

@description('Resource group for AI resources')
param resourceGroupName string

@description('Location for resources (must be supported by OpenAI)')
param location string

@description('Environment suffix (e.g., dev, test, prod)')
param environmentSuffix string

@description('OpenAI account name')
param openaiAccountName string

@description('VNet subscription id for private endpoints subnet')
param vnetSubscriptionId string

@description('VNet resource group')
param vnetResourceGroupName string

@description('VNet name')
param vnetName string

@description('Tags to apply')
param tags object = {}

@description('OpenAI model deployments to create')
param deployments array = []

var subnetName = 'snet-private-endpoints-${environmentSuffix}'

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module openai './modules/openai-account.bicep' = {
  scope: rg
  params: {
    location: location
    accountName: openaiAccountName
    tags: tags
    deployments: deployments
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
    peName: 'pe-${openaiAccountName}'
    targetResourceId: openai.outputs.accountId
    subnetId: privateEndpointsSubnet.id
    groupIds: [ 'account' ]
  }
}

output openaiAccountId string = openai.outputs.accountId
output openaiEndpoint string = openai.outputs.endpoint
output privateEndpointId string = pe.outputs.privateEndpointId

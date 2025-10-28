targetScope = 'subscription'

@description('Resource group for AI resources')
param resourceGroupName string

@description('Default location for resources')
param location string

@description('Environment suffix (e.g., dev, test, prod)')
param environmentSuffix string

@description('VNet subscription id for private endpoints subnet')
param vnetSubscriptionId string

@description('VNet resource group')
param vnetResourceGroupName string

@description('VNet name')
param vnetName string

@description('Tags to apply to all resources')
param tags object = {}

@description('Azure OpenAI account name')
param openaiAccountName string

@description('Computer Vision account name')
param visionAccountName string

@description('Document Intelligence account name')
param docIntAccountName string

@description('OpenAI model deployments to create')
param openaiDeployments array = []

@description('Override location for Azure OpenAI (defaults to location)')
param openaiLocation string = location

@description('Override location for Computer Vision (defaults to location)')
param visionLocation string = location

@description('Override location for Document Intelligence (defaults to location)')
param docIntLocation string = location

@description('Location for Private Endpoints (should match VNet region)')
param privateEndpointLocation string = location

var subnetName = 'snet-private-endpoints-${environmentSuffix}'

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

// Deploy Azure OpenAI
module openai './modules/openai-account.bicep' = {
  scope: rg
  params: {
    location: openaiLocation
    accountName: openaiAccountName
    tags: tags
  }
}

// Deploy OpenAI model deployments after account exists
module openaiModels './modules/openai-deployments.bicep' = if (length(openaiDeployments) > 0) {
  scope: rg
  dependsOn: [ openai ]
  params: {
    accountName: openaiAccountName
    deployments: openaiDeployments
  }
}

// Deploy Computer Vision
module vision './modules/vision-account.bicep' = {
  scope: rg
  params: {
    location: visionLocation
    accountName: visionAccountName
    tags: tags
  }
}

// Deploy Document Intelligence
module docint './modules/document-intelligence-account.bicep' = {
  scope: rg
  params: {
    location: docIntLocation
    accountName: docIntAccountName
    tags: tags
  }
}

// Existing VNet and subnet for private endpoints (may be cross-subscription)
resource existingVnet 'Microsoft.Network/virtualNetworks@2024-07-01' existing = {
  scope: resourceGroup(vnetSubscriptionId, vnetResourceGroupName)
  name: vnetName
}

resource privateEndpointsSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' existing = {
  name: subnetName
  parent: existingVnet
}

// Private Endpoints
module openaiPe './modules/private-endpoint.bicep' = {
  scope: rg
  dependsOn: [ openaiModels ]
  params: {
    location: privateEndpointLocation
    peName: 'pe-${openaiAccountName}'
    targetResourceId: openai.outputs.accountId
    subnetId: privateEndpointsSubnet.id
  }
}

module visionPe './modules/private-endpoint.bicep' = {
  scope: rg
  params: {
    location: privateEndpointLocation
    peName: 'pe-${visionAccountName}'
    targetResourceId: vision.outputs.accountId
    subnetId: privateEndpointsSubnet.id
  }
}

module docintPe './modules/private-endpoint.bicep' = {
  scope: rg
  params: {
    location: privateEndpointLocation
    peName: 'pe-${docIntAccountName}'
    targetResourceId: docint.outputs.accountId
    subnetId: privateEndpointsSubnet.id
  }
}

output openaiAccountId string = openai.outputs.accountId
output openaiEndpoint string = openai.outputs.endpoint
output openaiPrivateEndpointId string = openaiPe.outputs.privateEndpointId

output visionAccountId string = vision.outputs.accountId
output visionEndpoint string = vision.outputs.endpoint
output visionPrivateEndpointId string = visionPe.outputs.privateEndpointId

output docIntAccountId string = docint.outputs.accountId
output docIntEndpoint string = docint.outputs.endpoint
output docIntPrivateEndpointId string = docintPe.outputs.privateEndpointId

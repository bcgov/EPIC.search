@description('Location for the account')
param location string

@description('Resource group tags')
param tags object = {}

@description('Cognitive Services account name')
param accountName string

@description('Kind of cognitive account (OpenAI, CognitiveServices, FormRecognizer, ComputerVision)')
@allowed([ 'OpenAI', 'CognitiveServices', 'FormRecognizer', 'ComputerVision' ])
param kind string

@description('SKU for the account')
@allowed([ 'S0' ])
param sku string = 'S0'

@description('Restrict to vnet via private endpoints only')
@allowed([ 'Enabled', 'Disabled' ])
param publicNetworkAccess string = 'Disabled'

@description('Default action for network ACLs when public network is enabled')
@allowed([ 'Allow', 'Deny' ])
param networkDefaultAction string = 'Deny'

@description('System-assigned identity')
param enableIdentity bool = true

resource acct 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  kind: kind
  identity: {
    type: enableIdentity ? 'SystemAssigned' : 'None'
  }
  sku: {
    name: sku
  }
  properties: {
    customSubDomainName: accountName
    publicNetworkAccess: publicNetworkAccess
    networkAcls: {
      defaultAction: networkDefaultAction
      virtualNetworkRules: []
      ipRules: []
    }
  }
  tags: tags
}

output accountId string = acct.id
output endpoint string = acct.properties.endpoint
output name string = acct.name

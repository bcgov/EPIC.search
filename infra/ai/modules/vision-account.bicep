@description('Location for the Computer Vision account')
param location string

@description('Computer Vision account name')
param accountName string

@description('Resource tags')
param tags object = {}

@description('SKU for Computer Vision')
@allowed([ 'S1' ])
param sku string = 'S1'

@description('Public network access setting')
@allowed([ 'Enabled', 'Disabled' ])
param publicNetworkAccess string = 'Disabled'

@description('Default action for network ACLs when public network is enabled')
@allowed([ 'Allow', 'Deny' ])
param networkDefaultAction string = 'Allow'

@description('Enable system-assigned identity')
param enableIdentity bool = false

resource vision 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  tags: tags
  sku: {
    name: sku
  }
  kind: 'ComputerVision'
  identity: {
    type: enableIdentity ? 'SystemAssigned' : 'None'
  }
  properties: {
    customSubDomainName: accountName
    networkAcls: {
      defaultAction: networkDefaultAction
      virtualNetworkRules: []
      ipRules: []
    }
    allowProjectManagement: false
    publicNetworkAccess: publicNetworkAccess
  }
}

output accountId string = vision.id
output endpoint string = vision.properties.endpoint
output accountNameOut string = vision.name

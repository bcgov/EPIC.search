@description('Location for the Document Intelligence (Form Recognizer) account')
param location string

@description('Document Intelligence account name')
param accountName string

@description('Resource tags')
param tags object = {}

@description('SKU for Document Intelligence')
@allowed([ 'S0' ])
param sku string = 'S0'

@description('Public network access setting')
@allowed([ 'Enabled', 'Disabled' ])
param publicNetworkAccess string = 'Disabled'

@description('Default action for network ACLs when public network is enabled')
@allowed([ 'Allow', 'Deny' ])
param networkDefaultAction string = 'Allow'

@description('Enable system-assigned identity')
param enableIdentity bool = false

resource docint 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  tags: tags
  sku: {
    name: sku
  }
  kind: 'FormRecognizer'
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

output accountId string = docint.id
output endpoint string = docint.properties.endpoint
output accountNameOut string = docint.name

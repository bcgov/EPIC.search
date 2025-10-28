@description('Location for the OpenAI account')
param location string

@description('OpenAI account name')
param accountName string

@description('Resource tags')
param tags object = {}

@description('Enable Defender for AI (DefenderForAISettings)')
param enableDefenderForAI bool = true

@description('Public network access setting')
@allowed([ 'Enabled', 'Disabled' ])
param publicNetworkAccess string = 'Disabled'

@description('Default action for network ACLs when public network is enabled')
@allowed([ 'Allow', 'Deny' ])
param networkDefaultAction string = 'Deny'

@description('Allow project management in the account')
param allowProjectManagement bool = false

@description('OpenAI deployment entry')
type OpenAIDeployment = {
  name: string
  sku: {
    name: string
    capacity: int
  }
  properties: {
    model: {
      format: string
      name: string
      version: string
    }
    versionUpgradeOption: string
    currentCapacity: int
    raiPolicyName: string
  }
}

// (No model deployments parameter here; handled by modules/openai-deployments.bicep)

resource openai 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  tags: tags
  sku: {
    name: 'S0'
  }
  kind: 'OpenAI'
  properties: {
    apiProperties: {}
    customSubDomainName: accountName
    networkAcls: {
      defaultAction: networkDefaultAction
      virtualNetworkRules: []
      ipRules: []
    }
    allowProjectManagement: allowProjectManagement
    publicNetworkAccess: publicNetworkAccess
  }
}


resource defenderForAI 'Microsoft.CognitiveServices/accounts/defenderForAISettings@2025-06-01' = if (enableDefenderForAI) {
  parent: openai
  name: 'Default'
  properties: {
    state: 'Enabled'
  }
}

// Note: model deployments are created by modules/openai-deployments.bicep to avoid request conflicts

output accountId string = openai.id
output endpoint string = openai.properties.endpoint
output accountNameOut string = openai.name

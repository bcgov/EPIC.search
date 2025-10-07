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

@description('Model deployments to create')
param deployments OpenAIDeployment[] = [
  {
    name: 'gpt-41-nano'
    sku: {
      name: 'GlobalStandard'
      capacity: 75001
    }
    properties: {
      model: {
        format: 'OpenAI'
        name: 'gpt-4.1-nano'
        version: '2025-04-14'
      }
      versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
      currentCapacity: 75001
      raiPolicyName: 'Microsoft.DefaultV2'
    }
  }
]

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

@description('Enable RAI policy Microsoft.Default')
param enableRAIPolicyDefault bool = true

@description('Enable RAI policy Microsoft.DefaultV2')
param enableRAIPolicyDefaultV2 bool = true

resource raiDefault 'Microsoft.CognitiveServices/accounts/raiPolicies@2025-06-01' = if (enableRAIPolicyDefault) {
  parent: openai
  name: 'Microsoft.Default'
  properties: {
    mode: 'Blocking'
    contentFilters: [
      {
        name: 'Hate'
        severityThreshold: 'Medium'
        blocking: true
        enabled: true
        source: 'Prompt'
      }
      {
        name: 'Hate'
        severityThreshold: 'Medium'
        blocking: true
        enabled: true
        source: 'Completion'
      }
      {
        name: 'Sexual'
        severityThreshold: 'Medium'
        blocking: true
        enabled: true
        source: 'Prompt'
      }
      {
        name: 'Sexual'
        severityThreshold: 'Medium'
        blocking: true
        enabled: true
        source: 'Completion'
      }
      {
        name: 'Violence'
        severityThreshold: 'Medium'
        blocking: true
        enabled: true
        source: 'Prompt'
      }
      {
        name: 'Violence'
        severityThreshold: 'Medium'
        blocking: true
        enabled: true
        source: 'Completion'
      }
      {
        name: 'Selfharm'
        severityThreshold: 'Medium'
        blocking: true
        enabled: true
        source: 'Prompt'
      }
      {
        name: 'Selfharm'
        severityThreshold: 'Medium'
        blocking: true
        enabled: true
        source: 'Completion'
      }
    ]
  }
}

resource raiDefaultV2 'Microsoft.CognitiveServices/accounts/raiPolicies@2025-06-01' = if (enableRAIPolicyDefaultV2) {
  parent: openai
  name: 'Microsoft.DefaultV2'
  properties: {
    mode: 'Blocking'
    contentFilters: [
      {
        name: 'Hate'
        severityThreshold: 'Medium'
        blocking: true
        enabled: true
        source: 'Prompt'
      }
      {
        name: 'Hate'
        severityThreshold: 'Medium'
        blocking: true
        enabled: true
        source: 'Completion'
      }
      {
        name: 'Sexual'
        severityThreshold: 'Medium'
        blocking: true
        enabled: true
        source: 'Prompt'
      }
      {
        name: 'Sexual'
        severityThreshold: 'Medium'
        blocking: true
        enabled: true
        source: 'Completion'
      }
      {
        name: 'Violence'
        severityThreshold: 'Medium'
        blocking: true
        enabled: true
        source: 'Prompt'
      }
      {
        name: 'Violence'
        severityThreshold: 'Medium'
        blocking: true
        enabled: true
        source: 'Completion'
      }
      {
        name: 'Selfharm'
        severityThreshold: 'Medium'
        blocking: true
        enabled: true
        source: 'Prompt'
      }
      {
        name: 'Selfharm'
        severityThreshold: 'Medium'
        blocking: true
        enabled: true
        source: 'Completion'
      }
      {
        name: 'Jailbreak'
        blocking: true
        enabled: true
        source: 'Prompt'
      }
      {
        name: 'Protected Material Text'
        blocking: true
        enabled: true
        source: 'Completion'
      }
      {
        name: 'Protected Material Code'
        blocking: false
        enabled: true
        source: 'Completion'
      }
    ]
  }
}

resource defenderForAI 'Microsoft.CognitiveServices/accounts/defenderForAISettings@2025-06-01' = if (enableDefenderForAI) {
  parent: openai
  name: 'Default'
  properties: {
    state: 'Enabled'
  }
}

// Model deployments
resource modelDeployments 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = [for d in deployments: {
  parent: openai
  name: d.name
  sku: d.sku
  properties: d.properties
}]

output accountId string = openai.id
output endpoint string = openai.properties.endpoint
output accountNameOut string = openai.name

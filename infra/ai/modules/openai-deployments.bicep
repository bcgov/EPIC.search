@description('OpenAI account name (must exist in this resource group)')
param accountName string

@description('Model deployments to create')
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

param deployments OpenAIDeployment[]

resource openai 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: accountName
}

// Deploy models after account exists to avoid request conflicts
resource modelDeployments 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = [for d in deployments: {
  parent: openai
  name: d.name
  sku: d.sku
  properties: d.properties
}]

output deploymentNames array = [for d in deployments: d.name]

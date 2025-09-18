@description('Name of the Azure Automation Account')
param automationAccountName string

@description('Location for the automation account')
param location string = resourceGroup().location

@description('Tags to apply to all resources')
param tags object = {}

@description('SKU for the automation account')
@allowed(['Free', 'Basic'])
param sku string = 'Basic'

@description('Enable system assigned managed identity')
param enableSystemIdentity bool = true

// Create the Automation Account
resource automationAccount 'Microsoft.Automation/automationAccounts@2024-10-23' = {
  name: automationAccountName
  location: location
  tags: tags
  properties: {
    sku: {
      name: sku
    }
    encryption: {
      keySource: 'Microsoft.Automation'
    }
    publicNetworkAccess: true
    disableLocalAuth: false
  }
  identity: enableSystemIdentity ? {
    type: 'SystemAssigned'
  } : null
}

@description('Deploy PowerShell modules during deployment (can be unreliable)')
param deployModules bool = false

// Import required PowerShell modules for App Service management (optional)
// Note: Module installation during deployment can be unreliable
// It's recommended to install modules manually after deployment
resource azAccountsModule 'Microsoft.Automation/automationAccounts/modules@2023-11-01' = if (deployModules) {
  parent: automationAccount
  name: 'Az.Accounts'
  properties: {
    contentLink: {
      uri: 'https://www.powershellgallery.com/packages/Az.Accounts/2.12.5'
      version: '2.12.5'
    }
  }
}

resource azWebsitesModule 'Microsoft.Automation/automationAccounts/modules@2023-11-01' = if (deployModules) {
  parent: automationAccount
  name: 'Az.Websites'
  properties: {
    contentLink: {
      uri: 'https://www.powershellgallery.com/packages/Az.Websites/3.0.1'
      version: '3.0.1'
    }
  }
  dependsOn: [
    azAccountsModule
  ]
}

resource azProfileModule 'Microsoft.Automation/automationAccounts/modules@2023-11-01' = if (deployModules) {
  parent: automationAccount
  name: 'Az.Profile'
  properties: {
    contentLink: {
      uri: 'https://www.powershellgallery.com/packages/Az.Profile/1.2.1'
      version: '1.2.1'
    }
  }
  dependsOn: [
    azAccountsModule
  ]
}

// Outputs
output automationAccountId string = automationAccount.id
output automationAccountName string = automationAccount.name
output principalId string = enableSystemIdentity ? automationAccount.identity.principalId : ''
output tenantId string = enableSystemIdentity ? automationAccount.identity.tenantId : ''

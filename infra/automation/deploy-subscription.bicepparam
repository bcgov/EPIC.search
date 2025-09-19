using './deploy-subscription.bicep'

// Resource Group Configuration
param resourceGroupName = 'rg-tools-automation'
param location = 'East US'

// Automation Account Configuration
param automationAccountName = 'auto-myproject-tools'
param sku = 'Basic'

// Additional custom tags (optional)
// param customTags = {
//   Owner: 'platform-team'
//   CostCenter: 'tools'
// }

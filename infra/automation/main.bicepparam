using './main.bicep'

// Basic Configuration
param automationAccountName = 'auto-myproject'
param location = 'East US'

// Additional custom tags (optional)
// param customTags = {
//   Owner: 'MyTeam'
//   CostCenter: 'dev'
// }

// Automation Account SKU
param sku = 'Basic'  // 'Free' or 'Basic'

// Resource groups where your App Services are located
// The automation account will get Website Contributor permissions on these RGs
param appServiceResourceGroups = [
  'rg-myproject-apps-dev'
  'rg-myproject-apps-test'
]

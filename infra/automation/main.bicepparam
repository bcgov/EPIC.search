using './main.bicep'

// Basic Configuration
param automationAccountName = 'auto-myproject'
param location = 'Canada Central'

// Organizational Tags (use shared values)
param accountCoding = 'EPIC-001'
param billingGroup = 'EPIC-Team'
param ministryName = 'EPIC Services'

// Automation Account SKU
param sku = 'Basic'  // 'Free' or 'Basic'

// Resource groups where your App Services are located
// The automation account will get Website Contributor permissions on these RGs
param appServiceResourceGroups = [
  'rg-myproject-apps-dev'
  'rg-myproject-apps-test'
]

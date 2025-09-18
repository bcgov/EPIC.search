targetScope = 'subscription'

@description('Name of the resource group for automation resources')
param resourceGroupName string

@description('Location for the resource group and automation account')
param location string

@description('Name of the Azure Automation Account')
param automationAccountName string

@description('Additional custom tags to merge with required organizational tags')
param customTags object = {}

@description('SKU for the automation account')
@allowed(['Free', 'Basic'])
param sku string = 'Basic'

// Required organizational tags
var organizationalTags = {
  account_coding: 'your-account-coding'
  billing_group: 'your-billing-group'
  ministry_name: 'your-ministry'
}

// Combine organizational tags with any custom tags
var allTags = union(organizationalTags, customTags)

// Create resource group
resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: allTags
}

// Deploy the automation account solution to the resource group
module automationSolution './main.bicep' = {
  name: 'automationSolution'
  scope: resourceGroup
  params: {
    automationAccountName: automationAccountName
    location: location
    customTags: customTags
    sku: sku
    appServiceResourceGroups: [] // Will be configured separately via IAM scripts
  }
}

// Outputs
output resourceGroupId string = resourceGroup.id
output resourceGroupName string = resourceGroup.name
output automationAccountId string = automationSolution.outputs.automationAccountId
output automationAccountName string = automationSolution.outputs.automationAccountName
output principalId string = automationSolution.outputs.principalId

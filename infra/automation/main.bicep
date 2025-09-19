@description('Name of the Azure Automation Account')
param automationAccountName string

@description('Location for all resources')
param location string = resourceGroup().location

@description('Additional custom tags to merge with required organizational tags')
param customTags object = {}

@description('SKU for the automation account')
@allowed(['Free', 'Basic'])
param sku string = 'Basic'

@description('Resource groups where App Services are located (for IAM permissions)')
param appServiceResourceGroups array = []

@description('Deploy PowerShell modules during deployment (can be unreliable)')
param deployModules bool = false

// Note: Start/Stop App Services runbooks are now available as templates
// Use templates/start-stop-appservices/deploy-appservice-runbooks.bicep to deploy them

// Required organizational tags
var organizationalTags = {
  account_coding: 'your-account-coding'
  billing_group: 'your-billing-group'
  ministry_name: 'your-ministry'
}

// Combine organizational tags with any custom tags
var allTags = union(organizationalTags, customTags)

// Deploy the Automation Account
module automationAccount './modules/automation-account.bicep' = {
  name: 'automationAccount'
  params: {
    automationAccountName: automationAccountName
    location: location
    tags: allTags
    sku: sku
    enableSystemIdentity: true
    deployModules: deployModules
  }
}

// Deploy role assignments for each App Service resource group
module roleAssignments './modules/iam-assignment.bicep' = [for (rgName, index) in appServiceResourceGroups: {
  name: 'roleAssignment-${index}'
  scope: resourceGroup(rgName)
  params: {
    automationAccountPrincipalId: automationAccount.outputs.principalId
    roleDefinitionId: 'de139f84-1756-47ae-9be6-808fbbe84772' // Website Contributor
  }
}]

// Outputs
output automationAccountId string = automationAccount.outputs.automationAccountId
output automationAccountName string = automationAccount.outputs.automationAccountName
output principalId string = automationAccount.outputs.principalId
output roleAssignmentIds array = [for (rgName, index) in appServiceResourceGroups: roleAssignments[index].outputs.roleAssignmentId]

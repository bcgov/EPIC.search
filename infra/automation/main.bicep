@description('Name of the Azure Automation Account')
param automationAccountName string

@description('Location for all resources')
param location string = resourceGroup().location

@description('Account coding for billing and tracking')
param accountCoding string = 'EPIC-001'

@description('Billing group for cost allocation')
param billingGroup string = 'EPIC-Team'

@description('Ministry or department name')
param ministryName string = 'EPIC Services'

@description('Additional custom tags to merge with required organizational tags')
param customTags object = {}

@description('SKU for the automation account')
@allowed(['Free', 'Basic'])
param sku string = 'Basic'

@description('Resource groups where App Services are located (for IAM permissions)')
param appServiceResourceGroups array = []

@description('Resource groups where PostgreSQL servers are located (for IAM permissions)')
param postgreSQLResourceGroups array = []

@description('Custom role definition ID for PostgreSQL operations (if already created)')
param postgreSQLCustomRoleId string = ''

@description('Deploy PowerShell modules during deployment (can be unreliable)')
param deployModules bool = false

// Note: Start/Stop App Services runbooks are now available as templates
// Use templates/start-stop-appservices/deploy-appservice-runbooks.bicep to deploy them
// Note: Start/Stop PostgreSQL runbooks are now available as templates
// Use templates/start-stop-postgresql/deploy-postgresql-runbooks.bicep to deploy them

// Import the shared tags function
import { generateTags } from '../shared/tags.bicep'

// Generate tags using the shared function
var allTags = generateTags(accountCoding, billingGroup, ministryName, customTags)

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

// Deploy role assignments for each PostgreSQL resource group
module postgreSQLRoleAssignments './modules/iam-assignment.bicep' = [for (rgName, index) in postgreSQLResourceGroups: {
  name: 'postgreSQLRoleAssignment-${index}'
  scope: resourceGroup(rgName)
  params: {
    automationAccountPrincipalId: automationAccount.outputs.principalId
    roleDefinitionId: 'b24988ac-6180-42a0-ab88-20f7382dd24c' // Contributor (fallback)
    customRoleDefinitionId: postgreSQLCustomRoleId // Use custom role if provided
  }
}]

// Outputs
output automationAccountId string = automationAccount.outputs.automationAccountId
output automationAccountName string = automationAccount.outputs.automationAccountName
output principalId string = automationAccount.outputs.principalId
output roleAssignmentIds array = [for (rgName, index) in appServiceResourceGroups: roleAssignments[index].outputs.roleAssignmentId]
output postgreSQLRoleAssignmentIds array = [for (rgName, index) in postgreSQLResourceGroups: postgreSQLRoleAssignments[index].outputs.roleAssignmentId]

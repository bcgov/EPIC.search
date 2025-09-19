@description('Principal ID of the automation account managed identity')
param automationAccountPrincipalId string

@description('Comma-separated list of App Service names (e.g., "app1,app2,app3")')
param appServiceNames string

@description('Role definition ID for the required permissions')
@allowed([
  'de139f84-1756-47ae-9be6-808fbbe84772' // Website Contributor
  'b24988ac-6180-42a0-ab88-20f7382dd24c' // Contributor
])
param roleDefinitionId string = 'de139f84-1756-47ae-9be6-808fbbe84772' // Website Contributor

// Convert comma-separated string to array
var appServiceNameArray = split(replace(appServiceNames, ' ', ''), ',')

// Reference the existing App Services
resource appServices 'Microsoft.Web/sites@2023-12-01' existing = [for appServiceName in appServiceNameArray: {
  name: appServiceName
}]

// Create role assignments for all App Services
resource appServiceRoleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (appServiceName, index) in appServiceNameArray: {
  name: guid(appServices[index].id, automationAccountPrincipalId, roleDefinitionId)
  scope: appServices[index]
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitionId)
    principalId: automationAccountPrincipalId
    principalType: 'ServicePrincipal'
  }
}]

// Outputs
output roleAssignmentIds array = [for (appServiceName, index) in appServiceNameArray: appServiceRoleAssignments[index].id]
output appServiceIds array = [for (appServiceName, index) in appServiceNameArray: appServices[index].id]
output appServiceNames array = appServiceNameArray
output assignedAppServicesCount int = length(appServiceNameArray)

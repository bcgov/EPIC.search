@description('Principal ID of the automation account managed identity')
param automationAccountPrincipalId string

@description('Role definition ID for the required permissions')
@allowed([
  'de139f84-1756-47ae-9be6-808fbbe84772' // Website Contributor
  'b24988ac-6180-42a0-ab88-20f7382dd24c' // Contributor
])
param roleDefinitionId string = 'de139f84-1756-47ae-9be6-808fbbe84772' // Website Contributor

@description('Custom role definition ID (if using custom role instead of built-in role)')
param customRoleDefinitionId string = ''

// Create role assignment for the automation account to manage resources in this resource group
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, automationAccountPrincipalId, !empty(customRoleDefinitionId) ? customRoleDefinitionId : roleDefinitionId)
  properties: {
    roleDefinitionId: !empty(customRoleDefinitionId) ? customRoleDefinitionId : subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitionId)
    principalId: automationAccountPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output roleAssignmentId string = roleAssignment.id
output roleDefinitionId string = !empty(customRoleDefinitionId) ? customRoleDefinitionId : roleDefinitionId
output targetScope string = resourceGroup().id

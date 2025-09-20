targetScope = 'subscription'

@description('Environment suffix for the custom role name (e.g., Dev, Test, Prod)')
param environmentSuffix string

@description('Base name for the custom PostgreSQL Flexible Server Operator role')
param baseRoleName string = 'PostgreSQL Flexible Server Operator'

@description('Description for the custom role')
param roleDescription string = 'Custom role for automation account to start and stop PostgreSQL Flexible Servers'

@description('Assignable scopes for the custom role (default to subscription level)')
param assignableScopes array = [
  subscription().id
]

// Import the PostgreSQL custom role module
module postgreSQLCustomRole '../../modules/postgresql-custom-role.bicep' = {
  name: 'postgresql-custom-role-deployment'
  params: {
    customRoleName: '${baseRoleName} - ${environmentSuffix}'
    roleDescription: '${roleDescription} (${environmentSuffix} environment)'
    assignableScopes: assignableScopes
  }
}

// Outputs
output roleDefinitionId string = postgreSQLCustomRole.outputs.roleDefinitionId
output roleDefinitionName string = postgreSQLCustomRole.outputs.roleDefinitionName
output roleDefinitionGuid string = postgreSQLCustomRole.outputs.roleDefinitionGuid

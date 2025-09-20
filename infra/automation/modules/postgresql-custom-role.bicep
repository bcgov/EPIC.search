targetScope = 'subscription'

@description('Name for the custom PostgreSQL Flexible Server Operator role')
param customRoleName string = 'PostgreSQL Flexible Server Operator'

@description('Description for the custom role')
param roleDescription string = 'Custom role for automation account to start and stop PostgreSQL Flexible Servers'

@description('Assignable scopes for the custom role (default to subscription level)')
param assignableScopes array = [
  subscription().id
]

// Define the custom role for PostgreSQL Flexible Server operations
resource postgreSQLOperatorRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: guid(subscription().id, customRoleName)
  properties: {
    roleName: customRoleName
    description: roleDescription
    type: 'CustomRole'
    permissions: [
      {
        actions: [
          // Read permissions for PostgreSQL servers
          'Microsoft.DBforPostgreSQL/flexibleServers/read'
          'Microsoft.DBforPostgreSQL/flexibleServers/*/read'
          // Start and Stop permissions
          'Microsoft.DBforPostgreSQL/flexibleServers/start/action'
          'Microsoft.DBforPostgreSQL/flexibleServers/stop/action'
          // Basic read permissions for resource groups and subscriptions
          'Microsoft.Resources/subscriptions/resourceGroups/read'
        ]
        notActions: []
        dataActions: []
        notDataActions: []
      }
    ]
    assignableScopes: assignableScopes
  }
}

// Outputs
output roleDefinitionId string = postgreSQLOperatorRole.id
output roleDefinitionName string = postgreSQLOperatorRole.properties.roleName
output roleDefinitionGuid string = postgreSQLOperatorRole.name

using './deploy-postgresql-customrole.bicep'

param environmentSuffix = 'Test'
param baseRoleName = 'PostgreSQL Flexible Server Operator'
param roleDescription = 'Custom role for automation account to start and stop PostgreSQL Flexible Servers'
// assignableScopes will use the default value from the bicep file (subscription level)

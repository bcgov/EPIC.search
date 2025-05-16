@description('Environment name: dev, test, or prod')
param environment string

@description('Location for all resources')
param location string = resourceGroup().location

@description('Project or billing group tag')
param billingGroup string

@description('Additional tags to apply to resources')
param tags object = {}

@description('PostgreSQL server name')
param serverName string

@description('PostgreSQL server SKU')
param skuName string

@description('PostgreSQL storage size in GB')
param storageSizeGB int

@description('PostgreSQL version')
param version string

@description('PostgreSQL admin username')
param adminUser string

@description('PostgreSQL admin password')
@secure()
param adminPassword string

@description('VNet resource ID')
param vnetId string

@description('Subnet ID for PostgreSQL deployment')
param subnetId string

@description('Entra ID Admin Object/App ID for PostgreSQL')
param adminObjectId string = ''

// No longer needed - default is to not use private DNS zone
@description('Private DNS zone resource ID - not used as we skip DNS zone integration')
param privateDnsZoneId string = ''

// Deploy PostgreSQL flexible server
module postgresqlServer 'postgresql.bicep' = {
  name: 'deploy-postgresql'
  params: {
    environment: environment
    location: location
    billingGroup: billingGroup
    tags: tags
    serverName: serverName
    skuName: skuName
    storageSizeGB: storageSizeGB
    version: version
    adminUser: adminUser
    adminPassword: adminPassword
    vnetId: vnetId
    subnetId: subnetId
    adminObjectId: adminObjectId
  }
}

// Outputs
@description('PostgreSQL server resource ID')
output postgresqlServerId string = postgresqlServer.outputs.id
@description('PostgreSQL server name')
output postgresqlServerName string = postgresqlServer.outputs.name
@description('PostgreSQL server FQDN')
output postgresqlServerFqdn string = postgresqlServer.outputs.fullyQualifiedDomainName

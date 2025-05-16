@description('Name of the PostgreSQL server')
param serverName string

@description('Azure region where the server will be deployed')
param location string 

@description('VM size for the PostgreSQL server')
param skuName string

@description('Storage size in GB')
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

@description('Private DNS zone resource ID - not required as we skip DNS zone integration')
param privateDnsZoneId string = ''

@description('Skip private DNS zone integration - defaults to true since we don\'t need DNS zone integration')
param skipPrivateDnsZoneIntegration bool = true

@description('Environment name: dev, test, or prod')
param environment string

@description('Project or billing group tag')
param billingGroup string

@description('Additional tags to apply to resources')
param tags object = {}

// Combine default and custom tags
var defaultTags = {
  environment: environment
  billingGroup: billingGroup
  deployedBy: 'bicep'
}

var allTags = union(defaultTags, tags)

// Extract VNet name and resource group from the VNet ID
var vnetResourceId = split(vnetId, '/')
var vnetResourceGroup = vnetResourceId[4]
var vnetName = vnetResourceId[8]

// Reference the existing VNet
resource vnet 'Microsoft.Network/virtualNetworks@2021-02-01' existing = {
  name: vnetName
  scope: resourceGroup(vnetResourceGroup)
}

// Reference the existing subnet (already configured)
resource subnet 'Microsoft.Network/virtualNetworks/subnets@2021-02-01' existing = {
  name: last(split(subnetId, '/'))
  parent: vnet
}

// Network configuration - we only specify the delegated subnet without DNS zone
var networkConfig = {
  delegatedSubnetResourceId: subnetId
}

// Deploy the PostgreSQL Flexible Server
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2021-06-01' = {
  name: serverName
  location: location
  tags: allTags
  sku: {
    name: skuName
    tier: 'GeneralPurpose'
  }
  properties: {
    version: version
    administratorLogin: adminUser
    administratorLoginPassword: adminPassword
    authenticationConfig: empty(adminObjectId) ? null : {
      activeDirectoryAuth: {
        principalId: adminObjectId
      }
    }
    network: networkConfig
    highAvailability: {
      mode: 'Disabled'
    }
    storage: {
      storageSizeGB: storageSizeGB
      storageTier: 'Premium'
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
  }
}

// Deploy pgvector extension
resource pgvectorExtension 'Microsoft.DBforPostgreSQL/flexibleServers/extensions@2021-06-01' = {
  name: 'vector'
  parent: postgresServer
  properties: {
    extensionName: 'vector'
  }
}

// Outputs
@description('PostgreSQL server resource ID')
output id string = postgresServer.id
@description('PostgreSQL server name')
output name string = postgresServer.name
@description('PostgreSQL server FQDN')
output fullyQualifiedDomainName string = postgresServer.properties.fullyQualifiedDomainName

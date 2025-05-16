@description('Environment to deploy resources into (dev, test, prod)')
param environment string

@description('Azure region where resources will be deployed')
param location string = resourceGroup().location

@description('PostgreSQL admin password')
@secure()
param adminPassword string

// Import parameter files based on the environment
var networkingParams = loadJsonContent('parameters/${environment}/networking.parameters.bicep')
var databaseParams = loadJsonContent('parameters/${environment}/database.parameters.bicep')

// Deploy networking resources
module networking 'modules/networking/main.bicep' = {
  name: 'networking-deployment'
  params: {
    environment: environment
    location: location
    billingGroup: networkingParams.billingGroup
    tags: networkingParams.tags
    // Reference existing VNet name based on environment
    existingVirtualNetworkName: '${networkingParams.billingGroup}-${environment}-vwan-spoke'
    existingVirtualNetworkResourceGroup: 'your-rg-name-here' // Replace with the resource group where VNets are located
    dnsServers: networkingParams.dnsServers
    networkSecurityGroups: networkingParams.networkSecurityGroups
    subnets: networkingParams.subnets
  }
}

// Find the pgvector subnet ID from the networking outputs
var pgvectorSubnet = filter(networking.outputs.subnetIds, subnet => subnet.name == 'pgvector-subnet')
var pgvectorSubnetId = length(pgvectorSubnet) > 0 ? pgvectorSubnet[0].id : ''

// Deploy database resources
module database 'modules/database/main.bicep' = {
  name: 'database-deployment'
  params: {
    environment: environment
    location: location
    billingGroup: databaseParams.billingGroup
    tags: databaseParams.tags
    serverName: databaseParams.serverName
    skuName: databaseParams.skuName
    storageSizeGB: databaseParams.storageSizeGB
    version: databaseParams.version
    adminUser: databaseParams.adminUser
    adminPassword: adminPassword
    vnetId: networking.outputs.vnetId
    subnetId: pgvectorSubnetId
    adminObjectId: databaseParams.adminObjectId
  }
  dependsOn: [
    networking
  ]
}

// Output key resource IDs
output vnetId string = networking.outputs.vnetId
output vnetName string = networking.outputs.vnetName
output subnetIds array = networking.outputs.subnetIds
output nsgIds object = networking.outputs.nsgIds

// Database outputs
output postgresqlServerId string = database.outputs.postgresqlServerId
output postgresqlServerName string = database.outputs.postgresqlServerName
output postgresqlServerFqdn string = database.outputs.postgresqlServerFqdn

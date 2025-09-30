// Complete Networking Stack Deployment
// Deploys NSGs first, then Subnets in sequential order to avoid concurrency issues
targetScope = 'subscription'

@description('Environment suffix (e.g., dev, test, prod)')
param environmentSuffix string

@description('The Azure region where resources will be deployed')
param location string = 'Canada Central'

@description('Resource group name for NSGs')
param resourceGroupName string = 'rg-epic-search-network-${environmentSuffix}'

@description('The subscription ID where the VNet is located')
param vnetSubscriptionId string

@description('The resource group name where the VNet is located')
param vnetResourceGroupName string

@description('The name of the existing VNet')
param vnetName string

// NSG deployment parameters
@description('Deploy App Services NSG')
param deployAppServicesNSG bool = true

@description('Deploy PostgreSQL NSG')
param deployPostgreSQLNSG bool = true

@description('Deploy Private Endpoints NSG')
param deployPrivateEndpointsNSG bool = true

@description('Deploy VMs NSG')
param deployVMsNSG bool = true

// Subnet deployment parameters
@description('Deploy App Services subnet')
param deployAppServicesSubnet bool = true

@description('App Services subnet address prefix')
param appServicesSubnetAddressPrefix string

@description('Deploy PostgreSQL subnet')
param deployPostgreSQLSubnet bool = true

@description('PostgreSQL subnet address prefix')
param postgresqlSubnetAddressPrefix string

@description('Deploy Private Endpoints subnet')
param deployPrivateEndpointsSubnet bool = true

@description('Private Endpoints subnet address prefix')
param privateEndpointsSubnetAddressPrefix string

@description('Deploy VMs subnet')
param deployVMsSubnet bool = true

@description('VMs subnet address prefix')
param vmsSubnetAddressPrefix string

// Optional route table parameters (temporary)
@description('Route table ID for App Services subnet (optional)')
param appServicesRouteTableId string = ''

@description('Route table ID for PostgreSQL subnet (optional)')
param postgresqlRouteTableId string = ''

@description('Route table ID for Private Endpoints subnet (optional)')
param privateEndpointsRouteTableId string = ''

@description('Route table ID for VMs subnet (optional)')
param vmsRouteTableId string = ''

// Create or use existing resource group
resource networkingResourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
}

// PHASE 1: Deploy All NSGs First
module networkSecurityGroups 'nsg/nsg-resources.bicep' = {
  name: 'deploy-all-nsgs-${environmentSuffix}'
  scope: networkingResourceGroup
  params: {
    location: location
    environmentSuffix: environmentSuffix
    deployAppServicesNSG: deployAppServicesNSG
    deployPostgreSQLNSG: deployPostgreSQLNSG
    deployPrivateEndpointsNSG: deployPrivateEndpointsNSG
    deployVMsNSG: deployVMsNSG
  }
}

// PHASE 2: Deploy All Subnets After NSGs (with dependencies)
module subnets 'subnets/deploy-all-subnets.bicep' = {
  name: 'deploy-all-subnets-${environmentSuffix}'
  scope: networkingResourceGroup
  dependsOn: [
    networkSecurityGroups  // Wait for all NSGs to be created first
  ]
  params: {
    environmentSuffix: environmentSuffix
    vnetSubscriptionId: vnetSubscriptionId
    vnetResourceGroupName: vnetResourceGroupName
    vnetName: vnetName
    deployAppServicesSubnet: deployAppServicesSubnet
    appServicesSubnetAddressPrefix: appServicesSubnetAddressPrefix
    appServicesRouteTableId: appServicesRouteTableId
    deployPostgreSQLSubnet: deployPostgreSQLSubnet
    postgresqlSubnetAddressPrefix: postgresqlSubnetAddressPrefix
    postgresqlRouteTableId: postgresqlRouteTableId
    deployPrivateEndpointsSubnet: deployPrivateEndpointsSubnet
    privateEndpointsSubnetAddressPrefix: privateEndpointsSubnetAddressPrefix
    privateEndpointsRouteTableId: privateEndpointsRouteTableId
    deployVMsSubnet: deployVMsSubnet
    vmsSubnetAddressPrefix: vmsSubnetAddressPrefix
    vmsRouteTableId: vmsRouteTableId
  }
}

// Outputs from NSGs
output appServicesNSGId string = deployAppServicesNSG ? networkSecurityGroups.outputs.appServicesNSGId : ''
output postgresqlNSGId string = deployPostgreSQLNSG ? networkSecurityGroups.outputs.postgresqlNSGId : ''
output privateEndpointsNSGId string = deployPrivateEndpointsNSG ? networkSecurityGroups.outputs.privateEndpointsNSGId : ''
output vmsNSGId string = deployVMsNSG ? networkSecurityGroups.outputs.vmsNSGId : ''

// Outputs from Subnets
output appServicesSubnetId string = deployAppServicesSubnet ? subnets.outputs.appServicesSubnetId : ''
output postgresqlSubnetId string = deployPostgreSQLSubnet ? subnets.outputs.postgresqlSubnetId : ''
output privateEndpointsSubnetId string = deployPrivateEndpointsSubnet ? subnets.outputs.privateEndpointsSubnetId : ''
output vmsSubnetId string = deployVMsSubnet ? subnets.outputs.vmsSubnetId : ''

// VNet information
output vnetName string = vnetName
output vnetSubscriptionId string = vnetSubscriptionId
output vnetResourceGroupName string = vnetResourceGroupName

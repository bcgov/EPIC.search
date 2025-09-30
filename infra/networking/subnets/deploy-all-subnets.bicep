// Deploy All Subnets Template
// Orchestrates deployment of all subnet types with conditional deployment

@description('Environment suffix (e.g., dev, test, prod)')
param environmentSuffix string

@description('The subscription ID where the VNet is located')
param vnetSubscriptionId string

@description('The resource group name where the VNet is located')
param vnetResourceGroupName string

@description('The name of the existing VNet')
param vnetName string

// Subnet configuration parameters
@description('Deploy App Services subnet')
param deployAppServicesSubnet bool = true

@description('App Services subnet address prefix')
param appServicesSubnetAddressPrefix string = ''

@description('Deploy PostgreSQL subnet')
param deployPostgreSQLSubnet bool = true

@description('PostgreSQL subnet address prefix')
param postgresqlSubnetAddressPrefix string = ''

@description('Deploy Private Endpoints subnet')
param deployPrivateEndpointsSubnet bool = true

@description('Private Endpoints subnet address prefix')
param privateEndpointsSubnetAddressPrefix string = ''

@description('Deploy VMs subnet')
param deployVMsSubnet bool = true

@description('VMs subnet address prefix')
param vmsSubnetAddressPrefix string = ''

// Optional route table parameters (temporary - will be removed in future)
@description('Route table ID for App Services subnet (optional)')
param appServicesRouteTableId string = ''

@description('Route table ID for PostgreSQL subnet (optional)')
param postgresqlRouteTableId string = ''

@description('Route table ID for Private Endpoints subnet (optional)')
param privateEndpointsRouteTableId string = ''

@description('Route table ID for VMs subnet (optional)')
param vmsRouteTableId string = ''

// Deploy App Services Subnet
module appServicesSubnet 'templates/app-services-subnet.bicep' = if (deployAppServicesSubnet) {
  name: 'deploy-app-services-subnet-${environmentSuffix}'
  params: {
    environmentSuffix: environmentSuffix
    vnetSubscriptionId: vnetSubscriptionId
    vnetResourceGroupName: vnetResourceGroupName
    vnetName: vnetName
    subnetAddressPrefix: appServicesSubnetAddressPrefix
    routeTableId: appServicesRouteTableId
  }
}

// Deploy PostgreSQL Subnet (after App Services to avoid concurrency)
module postgresqlSubnet 'templates/postgresql-subnet.bicep' = if (deployPostgreSQLSubnet) {
  name: 'deploy-postgresql-subnet-${environmentSuffix}'
  dependsOn: [
    appServicesSubnet
  ]
  params: {
    environmentSuffix: environmentSuffix
    vnetSubscriptionId: vnetSubscriptionId
    vnetResourceGroupName: vnetResourceGroupName
    vnetName: vnetName
    subnetAddressPrefix: postgresqlSubnetAddressPrefix
    routeTableId: postgresqlRouteTableId
  }
}

// Deploy Private Endpoints Subnet (after PostgreSQL to avoid concurrency)
module privateEndpointsSubnet 'templates/private-endpoints-subnet.bicep' = if (deployPrivateEndpointsSubnet) {
  name: 'deploy-private-endpoints-subnet-${environmentSuffix}'
  dependsOn: [
    postgresqlSubnet
  ]
  params: {
    environmentSuffix: environmentSuffix
    vnetSubscriptionId: vnetSubscriptionId
    vnetResourceGroupName: vnetResourceGroupName
    vnetName: vnetName
    subnetAddressPrefix: privateEndpointsSubnetAddressPrefix
    routeTableId: privateEndpointsRouteTableId
  }
}

// Deploy VMs Subnet (after Private Endpoints to avoid concurrency)
module vmsSubnet 'templates/vms-subnet.bicep' = if (deployVMsSubnet) {
  name: 'deploy-vms-subnet-${environmentSuffix}'
  dependsOn: [
    privateEndpointsSubnet
  ]
  params: {
    environmentSuffix: environmentSuffix
    vnetSubscriptionId: vnetSubscriptionId
    vnetResourceGroupName: vnetResourceGroupName
    vnetName: vnetName
    subnetAddressPrefix: vmsSubnetAddressPrefix
    routeTableId: vmsRouteTableId
  }
}

// Outputs with conditional logic to handle when subnets are not deployed
output appServicesSubnetId string = deployAppServicesSubnet ? appServicesSubnet!.outputs.subnetId : ''
output appServicesSubnetName string = deployAppServicesSubnet ? appServicesSubnet!.outputs.subnetName : ''

output postgresqlSubnetId string = deployPostgreSQLSubnet ? postgresqlSubnet!.outputs.subnetId : ''
output postgresqlSubnetName string = deployPostgreSQLSubnet ? postgresqlSubnet!.outputs.subnetName : ''

output privateEndpointsSubnetId string = deployPrivateEndpointsSubnet ? privateEndpointsSubnet!.outputs.subnetId : ''
output privateEndpointsSubnetName string = deployPrivateEndpointsSubnet ? privateEndpointsSubnet!.outputs.subnetName : ''

output vmsSubnetId string = deployVMsSubnet ? vmsSubnet!.outputs.subnetId : ''
output vmsSubnetName string = deployVMsSubnet ? vmsSubnet!.outputs.subnetName : ''

output vnetName string = vnetName
output vnetSubscriptionId string = vnetSubscriptionId
output vnetResourceGroupName string = vnetResourceGroupName

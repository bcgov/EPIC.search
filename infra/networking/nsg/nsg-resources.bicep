// NSG Resources Template
// Deploys NSG resources within a resource group scope

@description('Location for all NSGs')
param location string

@description('Environment suffix for NSG names (e.g., dev, test, prod)')
param environmentSuffix string

@description('Deploy App Services NSG')
param deployAppServicesNSG bool = true

@description('Deploy PostgreSQL NSG')
param deployPostgreSQLNSG bool = true

@description('Deploy Private Endpoints NSG')
param deployPrivateEndpointsNSG bool = true

@description('Deploy VMs NSG')
param deployVMsNSG bool = true

// Deploy App Services NSG
resource appServicesNSG 'Microsoft.Network/networkSecurityGroups@2024-07-01' = if (deployAppServicesNSG) {
  name: 'nsg-app-services-${environmentSuffix}'
  location: location
  properties: {
    securityRules: [
      // Default rules - add specific rules as needed
    ]
  }
}

// Deploy PostgreSQL NSG
resource postgresqlNSG 'Microsoft.Network/networkSecurityGroups@2024-07-01' = if (deployPostgreSQLNSG) {
  name: 'nsg-postgresql-${environmentSuffix}'
  location: location
  properties: {
    securityRules: [
      // Default rules - add specific rules as needed
    ]
  }
}

// Deploy Private Endpoints NSG
resource privateEndpointsNSG 'Microsoft.Network/networkSecurityGroups@2024-07-01' = if (deployPrivateEndpointsNSG) {
  name: 'nsg-private-endpoints-${environmentSuffix}'
  location: location
  properties: {
    securityRules: [
      // Default rules - add specific rules as needed
    ]
  }
}

// Deploy VMs NSG
resource vmsNSG 'Microsoft.Network/networkSecurityGroups@2024-07-01' = if (deployVMsNSG) {
  name: 'nsg-vms-${environmentSuffix}'
  location: location
  properties: {
    securityRules: [
      // Default rules - add specific rules as needed
    ]
  }
}

// Outputs - only output if deployed
output appServicesNSGId string = deployAppServicesNSG ? appServicesNSG.id : ''
output postgresqlNSGId string = deployPostgreSQLNSG ? postgresqlNSG.id : ''
output privateEndpointsNSGId string = deployPrivateEndpointsNSG ? privateEndpointsNSG.id : ''
output vmsNSGId string = deployVMsNSG ? vmsNSG.id : ''

output appServicesNSGName string = deployAppServicesNSG ? appServicesNSG.name : ''
output postgresqlNSGName string = deployPostgreSQLNSG ? postgresqlNSG.name : ''
output privateEndpointsNSGName string = deployPrivateEndpointsNSG ? privateEndpointsNSG.name : ''
output vmsNSGName string = deployVMsNSG ? vmsNSG.name : ''

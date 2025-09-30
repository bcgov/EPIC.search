// Combined NSG Deployment
// Deploys all Network Security Groups for the networking infrastructure
targetScope = 'subscription'

@description('Location for all NSGs')
param location string = 'Canada Central'

@description('Environment suffix for NSG names (e.g., dev, test, prod)')
param environmentSuffix string

@description('Resource group name for NSGs')
param resourceGroupName string = 'rg-epic-search-network-${environmentSuffix}'

@description('Deploy App Services NSG')
param deployAppServicesNSG bool = true

@description('Deploy PostgreSQL NSG')
param deployPostgreSQLNSG bool = true

@description('Deploy Private Endpoints NSG')
param deployPrivateEndpointsNSG bool = true

@description('Deploy VMs NSG')
param deployVMsNSG bool = true

// Create or use existing resource group
resource networkingResourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
}

// Deploy NSGs in the resource group
module nsgDeployment 'nsg-resources.bicep' = {
  name: 'deploy-nsgs'
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

// Outputs - only output if deployed
output resourceGroupName string = networkingResourceGroup.name
output resourceGroupId string = networkingResourceGroup.id
output appServicesNSGId string = nsgDeployment.outputs.appServicesNSGId
output postgresqlNSGId string = nsgDeployment.outputs.postgresqlNSGId
output privateEndpointsNSGId string = nsgDeployment.outputs.privateEndpointsNSGId
output vmsNSGId string = nsgDeployment.outputs.vmsNSGId

output appServicesNSGName string = nsgDeployment.outputs.appServicesNSGName
output postgresqlNSGName string = nsgDeployment.outputs.postgresqlNSGName
output privateEndpointsNSGName string = nsgDeployment.outputs.privateEndpointsNSGName
output vmsNSGName string = nsgDeployment.outputs.vmsNSGName

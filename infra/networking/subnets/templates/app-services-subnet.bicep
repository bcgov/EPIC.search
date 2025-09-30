// App Services Subnet Template
// Creates a subnet for Azure App Services with VNet integration and associated NSG

@description('Environment suffix (e.g., dev, test, prod)')
param environmentSuffix string

@description('The subscription ID where the VNet is located')
param vnetSubscriptionId string

@description('The resource group name where the VNet is located')
param vnetResourceGroupName string

@description('The name of the existing VNet')
param vnetName string

@description('The address prefix for the app services subnet (e.g., 10.0.1.0/24)')
param subnetAddressPrefix string

@description('Optional route table ID for the subnet (temporary - will be removed in future)')
param routeTableId string = ''

// Reference the NSG created for app services (in current resource group)
resource appServicesNSG 'Microsoft.Network/networkSecurityGroups@2024-07-01' existing = {
  name: 'nsg-app-services-${environmentSuffix}'
}

// Deploy subnet to the existing VNet using a module to handle cross-scope deployment
module subnetDeployment 'subnet-deployment.bicep' = {
  name: 'deploy-app-services-subnet'
  scope: resourceGroup(vnetSubscriptionId, vnetResourceGroupName)
  params: {
    vnetName: vnetName
    subnetName: 'snet-app-services-${environmentSuffix}'
    subnetAddressPrefix: subnetAddressPrefix
    networkSecurityGroupId: appServicesNSG.id
    routeTableId: routeTableId
    delegations: [
      {
        name: 'Microsoft.Web.serverFarms'
        properties: {
          serviceName: 'Microsoft.Web/serverFarms'
        }
      }
    ]
    serviceEndpoints: [] // Empty by default for App Services
  }
}

// Outputs
output subnetId string = subnetDeployment.outputs.subnetId
output subnetName string = subnetDeployment.outputs.subnetName
output subnetAddressPrefix string = subnetDeployment.outputs.subnetAddressPrefix
output nsgId string = appServicesNSG.id
output vnetName string = subnetDeployment.outputs.vnetName
output vnetId string = subnetDeployment.outputs.vnetId

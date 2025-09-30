// PostgreSQL Subnet Template
// Creates a subnet for Azure Database for PostgreSQL Flexible Server with private endpoints

@description('Environment suffix (e.g., dev, test, prod)')
param environmentSuffix string

@description('The subscription ID where the VNet is located')
param vnetSubscriptionId string

@description('The resource group name where the VNet is located')
param vnetResourceGroupName string

@description('The name of the existing VNet')
param vnetName string

@description('The address prefix for the PostgreSQL subnet (e.g., 10.0.2.0/24)')
param subnetAddressPrefix string

@description('Optional route table ID for the subnet (temporary - will be removed in future)')
param routeTableId string = ''

// Reference the NSG created for PostgreSQL
resource postgresqlNSG 'Microsoft.Network/networkSecurityGroups@2024-07-01' existing = {
  name: 'nsg-postgresql-${environmentSuffix}'
}

// Deploy subnet to the existing VNet using a module to handle cross-scope deployment
module subnetDeployment 'subnet-deployment.bicep' = {
  name: 'deploy-postgresql-subnet'
  scope: resourceGroup(vnetSubscriptionId, vnetResourceGroupName)
  params: {
    vnetName: vnetName
    subnetName: 'snet-postgresql-${environmentSuffix}'
    subnetAddressPrefix: subnetAddressPrefix
    networkSecurityGroupId: postgresqlNSG.id
    routeTableId: routeTableId
    delegations: [
      {
        name: 'Microsoft.DBforPostgreSQL.flexibleServers'
        properties: {
          serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers'
        }
      }
    ]
    serviceEndpoints: [
      {
        service: 'Microsoft.Storage'
      }
    ]
  }
}

// Outputs
output subnetId string = subnetDeployment.outputs.subnetId
output subnetName string = subnetDeployment.outputs.subnetName
output subnetAddressPrefix string = subnetDeployment.outputs.subnetAddressPrefix
output nsgId string = postgresqlNSG.id
output vnetName string = subnetDeployment.outputs.vnetName
output vnetId string = subnetDeployment.outputs.vnetId

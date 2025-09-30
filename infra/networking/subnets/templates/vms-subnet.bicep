// VMs Subnet Template  
// Creates a subnet for virtual machines and compute resources

@description('Environment suffix (e.g., dev, test, prod)')
param environmentSuffix string

@description('The subscription ID where the VNet is located')
param vnetSubscriptionId string

@description('The resource group name where the VNet is located')
param vnetResourceGroupName string

@description('The name of the existing VNet')
param vnetName string

@description('The address prefix for the VMs subnet (e.g., 10.0.4.0/24)')
param subnetAddressPrefix string

@description('Optional route table ID for the subnet (temporary - will be removed in future)')
param routeTableId string = ''

// Reference the NSG created for VMs
resource vmsNSG 'Microsoft.Network/networkSecurityGroups@2024-07-01' existing = {
  name: 'nsg-vms-${environmentSuffix}'
}

// Deploy subnet to the existing VNet using a module to handle cross-scope deployment
module subnetDeployment 'subnet-deployment.bicep' = {
  name: 'deploy-vms-subnet'
  scope: resourceGroup(vnetSubscriptionId, vnetResourceGroupName)
  params: {
    vnetName: vnetName
    subnetName: 'snet-vms-${environmentSuffix}'
    subnetAddressPrefix: subnetAddressPrefix
    networkSecurityGroupId: vmsNSG.id
    routeTableId: routeTableId
    delegations: [] // VMs don't require subnet delegations
    serviceEndpoints: [
      {
        service: 'Microsoft.Storage'
      }
      {
        service: 'Microsoft.KeyVault'
      }
    ]
  }
}

// Outputs
output subnetId string = subnetDeployment.outputs.subnetId
output subnetName string = subnetDeployment.outputs.subnetName
output subnetAddressPrefix string = subnetDeployment.outputs.subnetAddressPrefix
output nsgId string = vmsNSG.id
output vnetName string = subnetDeployment.outputs.vnetName
output vnetId string = subnetDeployment.outputs.vnetId

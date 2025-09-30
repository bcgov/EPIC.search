targetScope = 'subscription'

@description('Name of the resource group for Bastion resources')
param bastionResourceGroupName string

@description('Name of the Azure Bastion resource')
param bastionName string

@description('Name of the virtual network where Bastion will be deployed')
param vnetName string

@description('Resource group name where the virtual network exists')
param vnetResourceGroupName string

@description('Location for all resources')
param location string

@description('Tags to apply to all resources - provided automatically via policy')
param tags object = {}

@description('SKU of the Bastion Host')
@allowed(['Basic', 'Standard', 'Developer', 'Premium'])
param bastionSku string = 'Developer'

@description('Address prefix for the AzureBastionSubnet (must be /26 or larger)')
param bastionSubnetAddressPrefix string

@description('Name of the NSG for the Bastion subnet')
param bastionNsgName string = 'nsg-bastion'

// Create resource group for Bastion resources (idempotent - won't fail if exists)
resource bastionResourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: bastionResourceGroupName
  location: location
  tags: tags
}

// Deploy the Azure Bastion solution to the resource group
module bastionDeployment './bastion.bicep' = {
  scope: bastionResourceGroup
  name: 'bastionDeployment'
  params: {
    bastionName: bastionName
    vnetName: vnetName
    vnetResourceGroupName: vnetResourceGroupName
    location: location
    tags: tags
    bastionSku: bastionSku
    bastionSubnetAddressPrefix: bastionSubnetAddressPrefix
    bastionNsgName: bastionNsgName
  }
}

// Outputs
output bastionResourceGroupName string = bastionResourceGroup.name
output bastionId string = bastionDeployment.outputs.bastionId
output bastionName string = bastionDeployment.outputs.bastionName
output bastionFqdn string = bastionDeployment.outputs.bastionFqdn
output bastionPublicIpAddress string = bastionDeployment.outputs.bastionPublicIpAddress
output bastionSubnetId string = bastionDeployment.outputs.bastionSubnetId

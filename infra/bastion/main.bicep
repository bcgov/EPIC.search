@description('Name of the Azure Bastion resource')
param bastionName string

@description('Name of the virtual network where Bastion will be deployed')
param vnetName string

@description('Resource group name where the virtual network exists')
param vnetResourceGroupName string = resourceGroup().name

@description('Location for all resources')
param location string = resourceGroup().location

@description('Tags to apply to all resources - provided automatically via policy')
param tags object = {}

@description('SKU of the Bastion Host')
@allowed(['Basic', 'Standard', 'Developer', 'Premium'])
param bastionSku string = 'Developer'

@description('Address prefix for the AzureBastionSubnet (must be /26 or larger)')
param bastionSubnetAddressPrefix string

@description('Name of the NSG for the Bastion subnet')
param bastionNsgName string = 'nsg-bastion'

// Deploy the Azure Bastion solution
module azureBastion './bastion.bicep' = {
  name: 'azureBastion'
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
output bastionId string = azureBastion.outputs.bastionId
output bastionName string = azureBastion.outputs.bastionName
output bastionFqdn string = azureBastion.outputs.bastionFqdn
output bastionPublicIpAddress string = azureBastion.outputs.bastionPublicIpAddress
output bastionSubnetId string = azureBastion.outputs.bastionSubnetId

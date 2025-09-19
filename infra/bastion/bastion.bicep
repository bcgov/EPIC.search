@description('Name of the Azure Bastion resource')
param bastionName string

@description('Name of the virtual network')
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

@description('Name of the NSG to apply to the AzureBastionSubnet')
param bastionNsgName string = 'nsg-bastion'

@description('Address prefix for the AzureBastionSubnet (must be /26 or larger)')
param bastionSubnetAddressPrefix string

// Reference existing NSG or create a new one
module bastionNsg './nsg.bicep' = {
  name: 'bastionNsg'
  params: {
    networkSecurityGroups_nsg_bastion_name: bastionNsgName
    location: location
  }
}

// Create Public IP for Bastion (not needed for Developer SKU)
resource bastionPublicIp 'Microsoft.Network/publicIPAddresses@2024-07-01' = if (bastionSku != 'Developer') {
  name: '${bastionName}-pip'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Regional'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
    publicIPAddressVersion: 'IPv4'
    dnsSettings: {
      domainNameLabel: toLower('${bastionName}-${uniqueString(resourceGroup().id)}')
    }
  }
}

// Create AzureBastionSubnet using module to handle cross-RG deployment
module bastionSubnet 'subnet.bicep' = {
  name: 'bastionSubnet'
  scope: resourceGroup(vnetResourceGroupName)
  params: {
    vnetName: vnetName
    subnetName: 'AzureBastionSubnet'
    subnetAddressPrefix: bastionSubnetAddressPrefix
    nsgId: bastionNsg.outputs.nsgId
  }
}

// Create Azure Bastion Host
resource bastionHost 'Microsoft.Network/bastionHosts@2024-01-01' = {
  name: bastionName
  location: location
  tags: tags
  sku: {
    name: bastionSku
  }
  properties: bastionSku == 'Developer' ? {
    // Developer SKU properties - no IP configurations needed
    virtualNetwork: {
      id: resourceId(vnetResourceGroupName, 'Microsoft.Network/virtualNetworks', vnetName)
    }
  } : {
    // Standard/Basic/Premium SKU properties - traditional IP configuration
    ipConfigurations: [
      {
        name: 'IpConf'
        properties: {
          subnet: {
            id: bastionSubnet.outputs.subnetId
          }
          publicIPAddress: {
            id: bastionPublicIp.id
          }
        }
      }
    ]
    // Scale units only apply to Basic/Standard/Premium SKUs, not Developer
    scaleUnits: 2
  }
}

// Outputs
output bastionId string = bastionHost.id
output bastionName string = bastionHost.name
output bastionFqdn string = bastionHost.properties.dnsName
output bastionPublicIpAddress string = bastionSku == 'Developer' ? 'N/A (Developer SKU)' : 'Check Azure Portal for Public IP'
output bastionSubnetId string = bastionSubnet.outputs.subnetId

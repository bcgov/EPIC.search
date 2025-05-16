@description('Environment name: dev, test, or prod')
param environment string

@description('Location for all resources')
param location string = resourceGroup().location

@description('Project or billing group tag')
param billingGroup string

@description('Additional tags to apply to resources')
param tags object = {}

@description('Name of the existing virtual network')
param existingVirtualNetworkName string

@description('Resource group where the existing virtual network is located')
param existingVirtualNetworkResourceGroup string

@description('DNS servers for the VNet')
param dnsServers array = []

@description('Array of Network Security Group configurations')
param networkSecurityGroups array = []

@description('Array of subnet configurations')
param subnets array = []

// Combine default and custom tags
var defaultTags = {
  environment: environment
  billingGroup: billingGroup
  deployedBy: 'bicep'
}

var allTags = union(defaultTags, tags)

// Get reference to the existing VNet
resource existingVnet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {
  name: existingVirtualNetworkName
  scope: resourceGroup(existingVirtualNetworkResourceGroup)
}

// Deploy NSGs first
module nsgResources 'nsg.bicep' = [for nsg in networkSecurityGroups: {
  name: 'deploy-nsg-${nsg.name}'
  params: {
    name: nsg.name
    location: location
    tags: allTags
    securityRules: contains(nsg, 'securityRules') ? nsg.securityRules : []
  }
}]

// Create a map of NSG names to resource IDs for subnet references
var nsgMap = reduce(range(0, length(networkSecurityGroups)), {}, (result, index) => 
  union(result, { '${networkSecurityGroups[index].name}': nsgResources[index].outputs.id })
)

// Update subnet configurations with NSG IDs
var subnetConfigs = [for subnet in subnets: {
  name: subnet.name
  addressPrefix: subnet.addressPrefix
  networkSecurityGroupId: contains(subnet, 'networkSecurityGroupName') ? nsgMap[subnet.networkSecurityGroupName] : ''
  serviceEndpoints: contains(subnet, 'serviceEndpoints') ? subnet.serviceEndpoints : []
  delegations: contains(subnet, 'delegations') ? subnet.delegations : []
  privateEndpointNetworkPolicies: contains(subnet, 'privateEndpointNetworkPolicies') ? subnet.privateEndpointNetworkPolicies : 'Enabled'
  privateLinkServiceNetworkPolicies: contains(subnet, 'privateLinkServiceNetworkPolicies') ? subnet.privateLinkServiceNetworkPolicies : 'Enabled'
}]

// Deploy subnets to the existing VNet
module subnetResources 'subnet.bicep' = [for (subnet, i) in subnetConfigs: {
  name: '${existingVirtualNetworkName}-subnet-${subnet.name}-${i}'
  params: {
    name: subnet.name
    addressPrefix: subnet.addressPrefix
    networkSecurityGroupId: contains(subnet, 'networkSecurityGroupId') ? subnet.networkSecurityGroupId : ''
    serviceEndpoints: contains(subnet, 'serviceEndpoints') ? subnet.serviceEndpoints : []
    delegations: contains(subnet, 'delegations') ? subnet.delegations : []
    privateEndpointNetworkPolicies: contains(subnet, 'privateEndpointNetworkPolicies') ? subnet.privateEndpointNetworkPolicies : 'Enabled'
    privateLinkServiceNetworkPolicies: contains(subnet, 'privateLinkServiceNetworkPolicies') ? subnet.privateLinkServiceNetworkPolicies : 'Enabled'
    virtualNetworkName: existingVnet.name
  }
  scope: resourceGroup(existingVirtualNetworkResourceGroup)
}]

@description('VNet resource ID')
output vnetId string = existingVnet.id
@description('VNet name')
output vnetName string = existingVnet.name
@description('Subnet resource IDs')
output subnetIds array = [for (subnet, i) in subnets: {
  name: subnet.name
  id: subnetResources[i].outputs.id
}]
@description('NSG resource IDs')
output nsgIds object = nsgMap

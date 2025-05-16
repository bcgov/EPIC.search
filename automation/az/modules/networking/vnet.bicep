@description('Name of the virtual network')
param name string

@description('Location for the resources')
param location string = resourceGroup().location

@description('Tags to apply to the VNet')
param tags object = {}

@description('Address prefixes for the virtual network')
param addressPrefixes array

@description('DNS servers for the virtual network')
param dnsServers array = []

@description('Array of subnet configurations')
param subnets array = []

@description('Array of virtual network peering configurations')
param peerings array = []

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: addressPrefixes
    }
    dhcpOptions: !empty(dnsServers) ? {
      dnsServers: dnsServers
    } : null
    subnets: []  // Subnets are deployed separately using the subnet module
    virtualNetworkPeerings: []  // Peerings are deployed separately
    enableDdosProtection: false
    privateEndpointVNetPolicies: 'Disabled'
  }
}

// Deploy each subnet using the subnet module
module subnetResources 'subnet.bicep' = [for (subnet, i) in subnets: {
  name: '${name}-subnet-${subnet.name}-${i}'
  params: {
    name: subnet.name
    addressPrefix: subnet.addressPrefix
    networkSecurityGroupId: contains(subnet, 'networkSecurityGroupId').? subnet.networkSecurityGroupId
    serviceEndpoints: contains(subnet, 'serviceEndpoints').? subnet.serviceEndpoints
    delegations: contains(subnet, 'delegations').? subnet.delegations
    privateEndpointNetworkPolicies: contains(subnet, 'privateEndpointNetworkPolicies').? subnet.privateEndpointNetworkPolicies
    privateLinkServiceNetworkPolicies: contains(subnet, 'privateLinkServiceNetworkPolicies').? subnet.privateLinkServiceNetworkPolicies
    virtualNetworkName: vnet.name
  }
}]

// Deploy each peering
resource peeringResources 'Microsoft.Network/virtualNetworks/virtualNetworkPeerings@2024-05-01' = [for peering in peerings: {
  name: '${vnet.name}/${peering.name}'
  properties: {
    peeringState: contains(peering, 'peeringState').? peering.peeringState
    peeringSyncLevel: contains(peering, 'peeringSyncLevel').? peering.peeringSyncLevel
    remoteVirtualNetwork: {
      id: peering.remoteVirtualNetworkId
    }
    allowVirtualNetworkAccess: contains(peering, 'allowVirtualNetworkAccess').? peering.allowVirtualNetworkAccess
    allowForwardedTraffic: contains(peering, 'allowForwardedTraffic').? peering.allowForwardedTraffic
    allowGatewayTransit: contains(peering, 'allowGatewayTransit').? peering.allowGatewayTransit
    useRemoteGateways: contains(peering, 'useRemoteGateways').? peering.useRemoteGateways
    doNotVerifyRemoteGateways: contains(peering, 'doNotVerifyRemoteGateways').? peering.doNotVerifyRemoteGateways
    peerCompleteVnets: contains(peering, 'peerCompleteVnets').? peering.peerCompleteVnets
  }
}]

@description('Resource ID of the created VNet')
output id string = vnet.id

@description('Name of the created VNet')
output name string = vnet.name

@description('Subnet resource IDs')
output subnetIds array = [for (subnet, i) in subnets: {
  name: subnet.name
  id: subnetResources[i].outputs.id
}]

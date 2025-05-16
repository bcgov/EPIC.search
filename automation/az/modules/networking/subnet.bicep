@description('Name of the subnet')
param name string

@description('CIDR address prefix for the subnet')
param addressPrefix string

@description('ID of the Network Security Group to associate with the subnet')
param networkSecurityGroupId string = ''

@description('Service endpoints to enable on the subnet')
param serviceEndpoints array = []

@description('Delegations for the subnet')
param delegations array = []

@description('Whether private endpoint network policies are enabled or disabled')
param privateEndpointNetworkPolicies string = 'Enabled'

@description('Whether private link service network policies are enabled or disabled')
param privateLinkServiceNetworkPolicies string = 'Enabled'

@description('Parent virtual network name')
param virtualNetworkName string

resource subnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  name: '${virtualNetworkName}/${name}'
  properties: {
    addressPrefix: addressPrefix
    networkSecurityGroup: !empty(networkSecurityGroupId) ? {
      id: networkSecurityGroupId
    } : null
    serviceEndpoints: serviceEndpoints
    delegations: delegations
    privateEndpointNetworkPolicies: privateEndpointNetworkPolicies
    privateLinkServiceNetworkPolicies: privateLinkServiceNetworkPolicies
  }
}

output id string = subnet.id
output name string = subnet.name

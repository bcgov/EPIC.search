@description('Location for the private endpoint')
param location string

@description('Name of the private endpoint')
param peName string

@description('Target Cognitive Services account id')
param targetResourceId string

@description('Subnet resource id for the private endpoint')
param subnetId string

@description('Group IDs (subresources). Typically ["account"]')
param groupIds array = [ 'account' ]

resource pe 'Microsoft.Network/privateEndpoints@2024-07-01' = {
  name: peName
  location: location
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: '${peName}-pls'
        properties: {
          privateLinkServiceId: targetResourceId
          groupIds: groupIds
          requestMessage: 'Approve private endpoint connection'
        }
      }
    ]
  }
}

output privateEndpointId string = pe.id

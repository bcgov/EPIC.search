@description('Name of the Network Security Group')
param name string

@description('Location for the resources')
param location string = resourceGroup().location

@description('Tags to apply to the NSG')
param tags object = {}

@description('Array of security rules to apply to the NSG')
param securityRules array = []

resource nsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    securityRules: securityRules
  }
}

@description('Resource ID of the created NSG')
output id string = nsg.id
@description('Name of the created NSG')
output name string = nsg.name

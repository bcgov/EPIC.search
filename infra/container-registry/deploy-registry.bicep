targetScope = 'subscription'

@description('Name of the resource group for Container Registry')
param resourceGroupName string

@description('Location for the resource group and registry')
param location string

@description('Name of the Azure Container Registry')
param registryName string

@description('SKU for the registry')
@allowed([ 'Basic', 'Standard', 'Premium' ])
param sku string = 'Standard'

@description('Enable admin user (for bootstrapping only; prefer AAD tokens)')
param adminUserEnabled bool = false

@description('Additional custom tags to merge with required organizational tags')
param customTags object = {}

@description('Optional scope maps to create on the registry')
param scopeMaps array = [] // [{ name: string, description: string, actions: string[] }]

@description('Role assignment mode for repository permissions. Use AzureRoleAssignments to enable tokens/scope maps; AbacRepositoryPermissions disables tokens/scope maps.')
@allowed([ 'AzureRoleAssignments', 'AbacRepositoryPermissions' ])
param roleAssignmentMode string = 'AbacRepositoryPermissions'

// Organizational tags (can be refactored to reuse shared if available)
var organizationalTags = {
  account_coding: 'your-account-coding'
  billing_group: 'your-billing-group'
  ministry_name: 'your-ministry'
}

var allTags = union(organizationalTags, customTags)

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: allTags
}

module registry './registry.bicep' = {
  scope: rg
  params: {
    location: location
    registryName: registryName
    sku: sku
    adminUserEnabled: adminUserEnabled
    tags: allTags
    scopeMaps: scopeMaps
    roleAssignmentMode: roleAssignmentMode
  }
}

output registryId string = registry.outputs.registryId
output registryLoginServer string = registry.outputs.registryLoginServer
output registryNameOut string = registry.outputs.registryNameOut

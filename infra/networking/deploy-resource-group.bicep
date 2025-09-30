// Subscription-level template to create the networking resource group
// This template should be deployed at subscription scope

targetScope = 'subscription'

@description('The Azure region where the resource group will be created')
param location string = 'Canada Central'

@description('Account coding for billing and cost management')
param accountCoding string

@description('Billing group identifier for cost allocation')
param billingGroup string

@description('Ministry name for governance and organization')
param ministryName string

@description('Environment suffix (e.g., dev, test, prod)')
param environmentSuffix string

@description('Custom tags to apply to the resource group in addition to standard tags')
param customTags object = {}

// Build tags directly since we can't use modules at subscription scope with resourceGroup scope modules
var standardTags = {
  account_coding: accountCoding
  billing_group: billingGroup
  ministry_name: ministryName
}

var allTags = union(standardTags, customTags, {
  Component: 'Networking'
  Purpose: 'Infrastructure'
  Environment: environmentSuffix
})

// Create the networking resource group
resource networkingResourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-epic-search-network-${environmentSuffix}'
  location: location
  tags: allTags
}

// Outputs
output resourceGroupName string = networkingResourceGroup.name
output resourceGroupId string = networkingResourceGroup.id
output location string = networkingResourceGroup.location
output tags object = networkingResourceGroup.tags

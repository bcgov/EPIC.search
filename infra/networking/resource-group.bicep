// Resource Group Template for EPIC.search Networking Infrastructure
// This creates the main resource group for all networking components

@description('The Azure region where resources will be deployed')
param location string = resourceGroup().location

@description('Account coding for billing and cost management')
param accountCoding string

@description('Billing group identifier for cost allocation')
param billingGroup string

@description('Ministry name for governance and organization')
param ministryName string

@description('Environment suffix (e.g., dev, test, prod)')
param environmentSuffix string

@description('Custom tags to apply to resources in addition to standard tags')
param customTags object = {}

// Import shared tags module
module tags '../shared/tags.bicep' = {
  name: 'resource-group-tags'
  params: {
    accountCoding: accountCoding
    billingGroup: billingGroup
    ministryName: ministryName
    customTags: union(customTags, {
      Component: 'Networking'
      Purpose: 'Infrastructure'
      Environment: environmentSuffix
    })
  }
}

// Note: Resource groups are created at subscription level, not within other resource groups
// This template serves as documentation and parameter validation
// The actual resource group must be created using Azure CLI or ARM template at subscription level

output resourceGroupName string = 'rg-epic-search-network-${environmentSuffix}'
output location string = location
output tags object = tags.outputs.tags
output recommendedCreationCommand string = 'az group create --name "rg-epic-search-network-${environmentSuffix}" --location "${location}"'

// Centralized tagging configuration for all infrastructure
// This file provides consistent tags across all infrastructure components

@description('Environment for the deployment (dev, test, prod)')
param environment string = 'dev'

@description('Project name')
param project string = 'myproject'

@description('Application or component name')
param application string

@description('Deployment timestamp')
param deployedAt string = utcNow('yyyy-MM-dd HH:mm:ss')

@description('Additional custom tags to merge with standard tags')
param customTags object = {}

// Standard organizational tags required by policy
var organizationalTags = {
  account_coding: 'your-account-coding'
  billing_group: 'your-billing-group'
  ministry_name: 'your-ministry'
}

// Standard operational tags
var operationalTags = {
  Environment: environment
  Project: project
  Application: application
  ManagedBy: 'bicep'
  DeployedAt: deployedAt
}

// Combine all tags
var allTags = union(organizationalTags, operationalTags, customTags)

// Function to generate tags for a specific application
func generateTags(environment string, project string, application string, customTags object) object => union(
  {
    account_coding: 'your-account-coding'
    billing_group: 'your-billing-group'
    ministry_name: 'your-ministry'
  },
  {
    Environment: environment
    Project: project
    Application: application
    ManagedBy: 'bicep'
  },
  customTags
)

// Outputs
output tags object = allTags
output organizationalTags object = organizationalTags
output operationalTags object = operationalTags

@description('Name of the existing Automation Account')
param automationAccountName string

@description('Location for the runbooks')
param location string = resourceGroup().location

@description('Account coding for billing and tracking')
param accountCoding string = 'EPIC-001'

@description('Billing group for cost allocation')
param billingGroup string = 'EPIC-Team'

@description('Ministry or department name')
param ministryName string = 'Citizens Services'

@description('Additional custom tags to merge with standard tags')
param customTags object = {}

// Import the shared tags function
import { generateTags } from '../../../shared/tags.bicep'

// Generate tags using the shared function
var tags = generateTags(accountCoding, billingGroup, ministryName, union(customTags, {
  Component: 'Runbooks'
  Purpose: 'ScheduledEmbedder'
}))

// Reference existing automation account
resource automationAccount 'Microsoft.Automation/automationAccounts@2024-10-23' existing = {
  name: automationAccountName
}

// Deploy ScheduledEmbedder runbook
resource scheduledEmbedderRunbook 'Microsoft.Automation/automationAccounts/runbooks@2024-10-23' = {
  parent: automationAccount
  name: 'ScheduledEmbedder'
  location: location
  tags: tags
  properties: {
    description: 'Automated embedding service that starts VM, processes embeddings, and stops VM and PostgreSQL'
    runbookType: 'PowerShell72'
    logVerbose: false
    logProgress: false
    logActivityTrace: 0
  }
}

// Outputs
output runbookName string = scheduledEmbedderRunbook.name
output runbookId string = scheduledEmbedderRunbook.id

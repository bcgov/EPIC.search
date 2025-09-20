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

@description('Deploy Start-PostgreSQL runbook')
param deployStartRunbook bool = true

@description('Deploy Stop-PostgreSQL runbook')
param deployStopRunbook bool = true

// Import the shared tags function
import { generateTags } from '../../../shared/tags.bicep'

// Generate tags using the shared function
var tags = generateTags(accountCoding, billingGroup, ministryName, union(customTags, {
  Component: 'Runbooks'
  Purpose: 'PostgreSQL-StartStop'
}))

// Reference existing automation account
resource automationAccount 'Microsoft.Automation/automationAccounts@2024-10-23' existing = {
  name: automationAccountName
}

// Deploy Start-PostgreSQL runbook
resource startPostgreSQLRunbook 'Microsoft.Automation/automationAccounts/runbooks@2024-10-23' = if (deployStartRunbook) {
  parent: automationAccount
  name: 'Start-PostgreSQL'
  location: location
  tags: tags
  properties: {
    description: 'PowerShell runbook to start Azure PostgreSQL servers'
    runbookType: 'PowerShell72'
    logVerbose: false
    logProgress: false
    logActivityTrace: 0
  }
}

// Deploy Stop-PostgreSQL runbook
resource stopPostgreSQLRunbook 'Microsoft.Automation/automationAccounts/runbooks@2024-10-23' = if (deployStopRunbook) {
  parent: automationAccount
  name: 'Stop-PostgreSQL'
  location: location
  tags: tags
  properties: {
    description: 'PowerShell runbook to stop Azure PostgreSQL servers'
    runbookType: 'PowerShell72'
    logVerbose: false
    logProgress: false
    logActivityTrace: 0
  }
}

// Outputs
output startRunbookId string = deployStartRunbook ? startPostgreSQLRunbook.id : ''
output stopRunbookId string = deployStopRunbook ? stopPostgreSQLRunbook.id : ''
output startRunbookName string = deployStartRunbook ? startPostgreSQLRunbook.name : ''
output stopRunbookName string = deployStopRunbook ? stopPostgreSQLRunbook.name : ''

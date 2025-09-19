@description('Name of the existing Automation Account')
param automationAccountName string

@description('Name of the runbook')
param runbookName string

@description('Description of the runbook')
param runbookDescription string = ''

@description('Type of runbook')
@allowed([
  'PowerShell'
  'PowerShell72'
  'PowerShellWorkflow'
  'GraphPowerShell'
  'Python2'
  'Python3'
])
param runbookType string = 'PowerShell72'

@description('Location for the runbook')
param location string = resourceGroup().location

@description('Tags to apply to the runbook')
param tags object = {}

@description('Enable verbose logging')
param logVerbose bool = false

@description('Enable progress logging')
param logProgress bool = false

@description('Activity trace level (0-3)')
@minValue(0)
@maxValue(3)
param logActivityTrace int = 0

// Reference existing automation account
resource automationAccount 'Microsoft.Automation/automationAccounts@2024-10-23' existing = {
  name: automationAccountName
}

// Create the runbook
resource runbook 'Microsoft.Automation/automationAccounts/runbooks@2024-10-23' = {
  parent: automationAccount
  name: runbookName
  location: location
  tags: tags
  properties: {
    description: runbookDescription
    runbookType: runbookType
    logVerbose: logVerbose
    logProgress: logProgress
    logActivityTrace: logActivityTrace
  }
}

// Outputs
output runbookId string = runbook.id
output runbookName string = runbook.name

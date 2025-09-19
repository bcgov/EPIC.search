@description('Name of the existing Automation Account')
param automationAccountName string

@description('Location for the runbooks')
param location string = resourceGroup().location

@description('Tags to apply to the runbooks')
param tags object = {}

@description('Deploy Start-AppServices runbook')
param deployStartRunbook bool = true

@description('Deploy Stop-AppServices runbook')
param deployStopRunbook bool = true

// Reference existing automation account
resource automationAccount 'Microsoft.Automation/automationAccounts@2024-10-23' existing = {
  name: automationAccountName
}

// Deploy Start-AppServices runbook
resource startAppServicesRunbook 'Microsoft.Automation/automationAccounts/runbooks@2024-10-23' = if (deployStartRunbook) {
  parent: automationAccount
  name: 'Start-AppServices'
  location: location
  tags: tags
  properties: {
    description: 'PowerShell runbook to start Azure App Services'
    runbookType: 'PowerShell72'
    logVerbose: false
    logProgress: false
    logActivityTrace: 0
  }
}

// Deploy Stop-AppServices runbook
resource stopAppServicesRunbook 'Microsoft.Automation/automationAccounts/runbooks@2024-10-23' = if (deployStopRunbook) {
  parent: automationAccount
  name: 'Stop-AppServices'
  location: location
  tags: tags
  properties: {
    description: 'PowerShell runbook to stop Azure App Services'
    runbookType: 'PowerShell72'
    logVerbose: false
    logProgress: false
    logActivityTrace: 0
  }
}

// Outputs
output startRunbookId string = deployStartRunbook ? startAppServicesRunbook.id : ''
output stopRunbookId string = deployStopRunbook ? stopAppServicesRunbook.id : ''
output startRunbookName string = deployStartRunbook ? startAppServicesRunbook.name : ''
output stopRunbookName string = deployStopRunbook ? stopAppServicesRunbook.name : ''

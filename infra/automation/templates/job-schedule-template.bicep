@description('Name of the existing Automation Account')
param automationAccountName string

@description('Name of the runbook to link to schedule')
param runbookName string

@description('Name of the schedule to link to runbook')
param scheduleName string

@description('Parameters to pass to the runbook when triggered by schedule')
param runbookParameters object = {}

// Reference existing automation account
resource automationAccount 'Microsoft.Automation/automationAccounts@2024-10-23' existing = {
  name: automationAccountName
}

// Reference existing runbook
resource runbook 'Microsoft.Automation/automationAccounts/runbooks@2024-10-23' existing = {
  parent: automationAccount
  name: runbookName
}

// Reference existing schedule
resource schedule 'Microsoft.Automation/automationAccounts/schedules@2024-10-23' existing = {
  parent: automationAccount
  name: scheduleName
}

// Create job schedule (links runbook to schedule)
resource jobSchedule 'Microsoft.Automation/automationAccounts/jobSchedules@2024-10-23' = {
  parent: automationAccount
  name: guid(runbook.id, schedule.id)
  properties: {
    runbook: {
      name: runbookName
    }
    schedule: {
      name: scheduleName
    }
    parameters: runbookParameters
  }
}

// Outputs
output jobScheduleId string = jobSchedule.id
output linkedRunbook string = runbookName
output linkedSchedule string = scheduleName

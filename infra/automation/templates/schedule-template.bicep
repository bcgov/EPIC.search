@description('Name of the existing Automation Account')
param automationAccountName string

@description('Name of the schedule')
param scheduleName string

@description('Description of the schedule')
param scheduleDescription string = ''

@description('Start time for the schedule (ISO 8601 format)')
param startTime string

@description('Time zone for the schedule')
param timeZone string = 'UTC' // Default to UTC, can be overridden

@description('Frequency of the schedule')
@allowed(['OneTime', 'Day', 'Hour', 'Week', 'Month'])
param frequency string = 'Day'

@description('Interval for the schedule (e.g., every 1 day)')
param interval int = 1

@description('Expiry time for the schedule (optional, ISO 8601 format)')
param expiryTime string = ''

@description('Days of the week for weekly schedules (e.g., ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])')
param weekDays array = []

// Note: Azure Automation schedules do not support tags directly
// Tags are applied at the automation account level

// Reference existing automation account
resource automationAccount 'Microsoft.Automation/automationAccounts@2024-10-23' existing = {
  name: automationAccountName
}

// Create the schedule
resource schedule 'Microsoft.Automation/automationAccounts/schedules@2024-10-23' = {
  parent: automationAccount
  name: scheduleName
  properties: {
    description: scheduleDescription
    startTime: startTime
    expiryTime: empty(expiryTime) ? null : expiryTime
    interval: interval
    frequency: frequency
    timeZone: timeZone
    advancedSchedule: !empty(weekDays) ? {
      weekDays: weekDays
    } : null
  }
}

// Outputs
output scheduleId string = schedule.id
output scheduleName string = schedule.name

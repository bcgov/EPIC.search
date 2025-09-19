# Automation Scheduling Guide

This guide shows how to create schedules for your automation runbooks to run automatically.

## 🕐 Common Scheduling Scenarios

### Business Hours Start/Stop (8 AM PST Start, 5 PM PST Stop)

This example creates schedules to start App Services at 8 AM PST and stop them at 5 PM PST, Monday through Friday.

## 📅 Schedule Templates

### 1. Morning Start Schedule (8 AM PST, Weekdays)

```powershell
# Deploy morning start schedule
az deployment group create `
  --resource-group "rg-tools-automation" `
  --template-file templates/schedule-template.bicep `
  --parameters `
    automationAccountName="auto-myproject-tools" `
    scheduleName="MorningStart-Weekdays" `
    scheduleDescription="Start App Services at 8 AM PST, Monday-Friday" `
    startTime="2025-01-01T08:00:00" `
    timeZone="America/Vancouver" `
    frequency="Week" `
    interval=1
```

### 2. Evening Stop Schedule (5 PM PST, Weekdays)

```powershell
# Deploy evening stop schedule
az deployment group create `
  --resource-group "rg-tools-automation" `
  --template-file templates/schedule-template.bicep `
  --parameters `
    automationAccountName="auto-myproject-tools" `
    scheduleName="EveningStop-Weekdays" `
    scheduleDescription="Stop App Services at 5 PM PST, Monday-Friday" `
    startTime="2025-01-01T17:00:00" `
    timeZone="America/Vancouver" `
    frequency="Week" `
    interval=1
```

### 3. Link Start Runbook to Morning Schedule

```powershell
# Link Start-AppServices runbook to morning schedule
az deployment group create `
  --resource-group "rg-tools-automation" `
  --template-file templates/job-schedule-template.bicep `
  --parameters `
    automationAccountName="auto-myproject-tools" `
    runbookName="Start-AppServices" `
    scheduleName="MorningStart-Weekdays" `
    runbookParameters='{
      "ResourceGroupName": "rg-myproject-apps",
      "AppServiceNames": "app1,app2,app3",
      "SubscriptionId": "your-subscription-id",
      "WaitForStartup": true
    }'
```

### 4. Link Stop Runbook to Evening Schedule

```powershell
# Link Stop-AppServices runbook to evening schedule
az deployment group create `
  --resource-group "rg-tools-automation" `
  --template-file templates/job-schedule-template.bicep `
  --parameters `
    automationAccountName="auto-myproject-tools" `
    runbookName="Stop-AppServices" `
    scheduleName="EveningStop-Weekdays" `
    runbookParameters='{
      "ResourceGroupName": "rg-myproject-apps",
      "AppServiceNames": "app1,app2,app3",
      "SubscriptionId": "your-subscription-id",
      "WaitForShutdown": true
    }'
```

## 🔧 Alternative: PowerShell Management

You can also create schedules using PowerShell commands:

```powershell
# Create morning start schedule
New-AzAutomationSchedule `
  -AutomationAccountName "auto-myproject-tools" `
  -ResourceGroupName "rg-tools-automation" `
  -Name "MorningStart-Weekdays" `
  -StartTime "08:00" `
  -DayInterval 1 `
  -TimeZone "America/Vancouver"

# Link runbook to schedule
Register-AzAutomationScheduledRunbook `
  -AutomationAccountName "auto-myproject-tools" `
  -ResourceGroupName "rg-tools-automation" `
  -RunbookName "Start-AppServices" `
  -ScheduleName "MorningStart-Weekdays" `
  -Parameters @{
    ResourceGroupName = "rg-myproject-apps"
    AppServiceNames = "app1,app2,app3"
    SubscriptionId = "your-subscription-id"
    WaitForStartup = $true
  }
```

## 📋 Schedule Management

### List All Schedules
```powershell
Get-AzAutomationSchedule `
  -AutomationAccountName "auto-myproject-tools" `
  -ResourceGroupName "rg-tools-automation"
```

### Disable/Enable Schedule
```powershell
# Disable schedule
Set-AzAutomationSchedule `
  -AutomationAccountName "auto-myproject-tools" `
  -ResourceGroupName "rg-tools-automation" `
  -Name "MorningStart-Weekdays" `
  -IsEnabled $false

# Enable schedule
Set-AzAutomationSchedule `
  -AutomationAccountName "auto-myproject-tools" `
  -ResourceGroupName "rg-tools-automation" `
  -Name "MorningStart-Weekdays" `
  -IsEnabled $true
```

## 🕐 Time Zone Reference

**PST/PDT (Vancouver)**: `America/Vancouver`
**EST/EDT (Toronto)**: `America/Toronto`
**UTC**: `UTC`

## 📝 Best Practices

1. **Use descriptive schedule names** that indicate purpose and frequency
2. **Set appropriate time zones** for your business hours
3. **Test schedules** with one-time runs before enabling recurring schedules
4. **Monitor job history** to ensure schedules are working correctly
5. **Use different schedules** for different environments (dev/test/prod)
param(
    [string]$SubscriptionId,
    [string]$AutomationAccountName,
    [string]$ResourceGroupName
)

Write-Output "Publishing ScheduledEmbedder runbook..."
Write-Output "Subscription: $SubscriptionId"
Write-Output "Automation Account: $AutomationAccountName"
Write-Output "Resource Group: $ResourceGroupName"

# Connect to Azure
Connect-AzAccount -Identity

# Set subscription context
Set-AzContext -SubscriptionId $SubscriptionId

try {
    # Get the path to the PowerShell script
    $scriptPath = Join-Path $PSScriptRoot "ScheduledEmbedder.ps1"
    
    if (!(Test-Path $scriptPath)) {
        throw "ScheduledEmbedder.ps1 not found at $scriptPath"
    }
    
    Write-Output "Found ScheduledEmbedder.ps1 at: $scriptPath"
    
    # Import the runbook
    Write-Output "Importing runbook to Automation Account..."
    Import-AzAutomationRunbook `
        -AutomationAccountName $AutomationAccountName `
        -ResourceGroupName $ResourceGroupName `
        -Name "ScheduledEmbedder" `
        -Type PowerShell `
        -Path $scriptPath `
        -Force
    
    Write-Output "Runbook imported successfully."
    
    # Publish the runbook
    Write-Output "Publishing runbook..."
    Publish-AzAutomationRunbook `
        -AutomationAccountName $AutomationAccountName `
        -ResourceGroupName $ResourceGroupName `
        -Name "ScheduledEmbedder"
    
    Write-Output "ScheduledEmbedder runbook published successfully!"
    
} catch {
    Write-Error "Error publishing ScheduledEmbedder runbook: $($_.Exception.Message)"
    throw
}
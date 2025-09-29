param(
    [string]$SubscriptionId,
    [string]$AutomationAccountName,
    [string]$ResourceGroupName
)

Write-Output "Publishing VM runbooks..."
Write-Output "Subscription: $SubscriptionId"
Write-Output "Automation Account: $AutomationAccountName"
Write-Output "Resource Group: $ResourceGroupName"

# Connect to Azure
Connect-AzAccount -Identity

# Set subscription context
Set-AzContext -SubscriptionId $SubscriptionId

try {
    # Get the path to the PowerShell scripts
    $startScriptPath = Join-Path $PSScriptRoot "Start-VMs.ps1"
    $stopScriptPath = Join-Path $PSScriptRoot "Stop-VMs.ps1"
    
    if (!(Test-Path $startScriptPath)) {
        throw "Start-VMs.ps1 not found at $startScriptPath"
    }
    
    if (!(Test-Path $stopScriptPath)) {
        throw "Stop-VMs.ps1 not found at $stopScriptPath"
    }
    
    Write-Output "Found PowerShell scripts:"
    Write-Output "- Start-VMs.ps1 at: $startScriptPath"
    Write-Output "- Stop-VMs.ps1 at: $stopScriptPath"
    
    # Import Start-VMs runbook
    Write-Output "Importing Start-VMs runbook..."
    Import-AzAutomationRunbook `
        -AutomationAccountName $AutomationAccountName `
        -ResourceGroupName $ResourceGroupName `
        -Name "Start-VMs" `
        -Type PowerShell `
        -Path $startScriptPath `
        -Force
    
    # Publish Start-VMs runbook
    Write-Output "Publishing Start-VMs runbook..."
    Publish-AzAutomationRunbook `
        -AutomationAccountName $AutomationAccountName `
        -ResourceGroupName $ResourceGroupName `
        -Name "Start-VMs"
    
    # Import Stop-VMs runbook
    Write-Output "Importing Stop-VMs runbook..."
    Import-AzAutomationRunbook `
        -AutomationAccountName $AutomationAccountName `
        -ResourceGroupName $ResourceGroupName `
        -Name "Stop-VMs" `
        -Type PowerShell `
        -Path $stopScriptPath `
        -Force
    
    # Publish Stop-VMs runbook
    Write-Output "Publishing Stop-VMs runbook..."
    Publish-AzAutomationRunbook `
        -AutomationAccountName $AutomationAccountName `
        -ResourceGroupName $ResourceGroupName `
        -Name "Stop-VMs"
    
    Write-Output "VM runbooks published successfully!"
    
} catch {
    Write-Error "Error publishing VM runbooks: $($_.Exception.Message)"
    throw
}
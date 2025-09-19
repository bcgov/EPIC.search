# Script for stopping Azure App Services
# This script stops App Services in the specified resource group

param (
    [Parameter(Mandatory = $true)]
    [string] $ResourceGroupName,

    [Parameter(Mandatory = $true)]
    [string] $AppServiceNames,
    
    [Parameter(Mandatory = $true)]
    [string] $SubscriptionId,

    [Parameter()]
    [switch] $WaitForShutdown
)

try {
    Write-Output "Starting App Service stop automation runbook..."
    Write-Output "Resource Group: $ResourceGroupName"
    Write-Output "App Services: $AppServiceNames"
    Write-Output "Subscription: $SubscriptionId"
    
    # Connect using managed identity
    Write-Output "Connecting to Azure using Managed Identity..."
    Connect-AzAccount -Identity

    # Set the subscription context
    Write-Output "Setting subscription context..."
    Set-AzContext -SubscriptionId $SubscriptionId

    # Split the comma-separated string into an array
    $appServiceArray = $AppServiceNames.Split(',').Trim()
    Write-Output "Processing $($appServiceArray.Count) App Service(s)..."

    foreach ($appServiceName in $appServiceArray) {
        Write-Output "Stopping App Service: $appServiceName"
        
        # Check if the App Service exists
        try {
            $webApp = Get-AzWebApp -ResourceGroupName $ResourceGroupName -Name $appServiceName -ErrorAction Stop
            Write-Output "Found App Service: $appServiceName (Current State: $($webApp.State))"
            
            if ($webApp.State -eq "Stopped") {
                Write-Output "App Service '$appServiceName' is already stopped"
                continue
            }
        }
        catch {
            Write-Error "App Service '$appServiceName' not found in resource group '$ResourceGroupName': $($_.Exception.Message)"
            continue
        }

        # Stop the App Service
        try {
            Write-Output "Sending stop command to App Service: $appServiceName"
            Stop-AzWebApp -ResourceGroupName $ResourceGroupName -Name $appServiceName
            Write-Output "Stop command sent successfully for: $appServiceName"

            if ($WaitForShutdown) {
                Write-Output "Waiting for App Service to stop..."
                $timeout = 300 # 5 minutes timeout
                $elapsed = 0
                $interval = 10
                
                do {
                    Start-Sleep -Seconds $interval
                    $elapsed += $interval
                    $webApp = Get-AzWebApp -ResourceGroupName $ResourceGroupName -Name $appServiceName
                    Write-Output "Current state: $($webApp.State) (Elapsed: ${elapsed}s)"
                    
                    if ($elapsed -ge $timeout) {
                        Write-Warning "Timeout reached while waiting for App Service '$appServiceName' to stop"
                        break
                    }
                } while ($webApp.State -ne "Stopped")
                
                if ($webApp.State -eq "Stopped") {
                    Write-Output "App Service '$appServiceName' is now stopped"
                } else {
                    Write-Warning "App Service '$appServiceName' may not have stopped successfully"
                }
            }
        }
        catch {
            Write-Error "Failed to stop App Service '$appServiceName': $($_.Exception.Message)"
        }
    }
    
    Write-Output "App Service stop automation completed successfully"
}
catch {
    Write-Error "Fatal error in runbook execution: $($_.Exception.Message)"
    Write-Error $_.Exception.StackTrace
    exit 1
}
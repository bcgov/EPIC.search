param(
    [string]$SubscriptionId,
    [string]$ResourceGroupName,
    [string]$PostgreSQLNames
)

# Ensure PostgreSQLNames parameter is provided
if (-not $PostgreSQLNames) {
    Write-Error "No PostgreSQL server names provided. Exiting."
    Exit
}

# Output the parameters
Write-Output "Subscription ID: $SubscriptionId"
Write-Output "Resource Group Name: $ResourceGroupName"
Write-Output "PostgreSQL Names: $PostgreSQLNames"

# Connect to Azure using managed identity
Connect-AzAccount -Identity

# Set the subscription context dynamically
Set-AzContext -SubscriptionId $SubscriptionId

# Ensure Az.PostgreSql module is available
$module = Get-Module -ListAvailable -Name Az.PostgreSql
if (-not $module) {
    Write-Output "Az.PostgreSql module is missing. Installing..."
    Install-Module Az.PostgreSql -Force
}

# Import the module to ensure it's loaded in the session
Import-Module Az.PostgreSql

# Split PostgreSQLNames parameter into an array
$PostgreSQLNameArray = $PostgreSQLNames -split ','

# Stop PostgreSQL instances with state validation
foreach ($PostgreSQLServerName in $PostgreSQLNameArray) {
    Write-Output "Checking state of PostgreSQL Server: $PostgreSQLServerName"

    # Get server properties
    $server = Get-AzPostgreSqlFlexibleServer -ResourceGroupName $ResourceGroupName -Name $PostgreSQLServerName

    if ($server -eq $null) {
        Write-Output "ERROR: PostgreSQL Server '$PostgreSQLServerName' not found. Skipping..."
        continue
    }

    if ($server.State -eq "Ready") {
        Write-Output "PostgreSQL Server '$PostgreSQLServerName' is in 'Ready' state. Stopping..."
        Stop-AzPostgreSqlFlexibleServer -ResourceGroupName $ResourceGroupName -Name $PostgreSQLServerName
        Write-Output "PostgreSQL Server '$PostgreSQLServerName' has been stopped successfully."
    } elseif ($server.State -eq "Stopped") {
        Write-Output "INFO: PostgreSQL Server '$PostgreSQLServerName' is already stopped. Skipping shutdown."
    } else {
        Write-Output "WARNING: PostgreSQL Server '$PostgreSQLServerName' is in unexpected state '$($server.State)'. Skipping shutdown."
    }
}

Write-Output "PostgreSQL shutdown process completed!"
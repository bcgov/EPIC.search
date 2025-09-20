param(
    [string]$SubscriptionId,
    [string]$ResourceGroupName,
    [string]$PostgreSQLNames
)

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

# Start PostgreSQL instances with state validation
foreach ($PostgreSQLServerName in $PostgreSQLNameArray) {
    Write-Output "Checking state of PostgreSQL Server: $PostgreSQLServerName"

    # Get server properties
    $server = Get-AzPostgreSqlFlexibleServer -ResourceGroupName $ResourceGroupName -Name $PostgreSQLServerName

    if ($server -eq $null) {
        Write-Output "ERROR: PostgreSQL Server '$PostgreSQLServerName' not found. Skipping..."
        continue
    }

    if ($server.State -eq "Stopped") {
        Write-Output "PostgreSQL Server '$PostgreSQLServerName' is in 'Stopped' state. Starting..."
        Start-AzPostgreSqlFlexibleServer -ResourceGroupName $ResourceGroupName -Name $PostgreSQLServerName
        Write-Output "PostgreSQL Server '$PostgreSQLServerName' has been started successfully."
    } elseif ($server.State -eq "Ready") {
        Write-Output "INFO: PostgreSQL Server '$PostgreSQLServerName' is already running ('Ready' state). Skipping startup."
    } else {
        Write-Output "WARNING: PostgreSQL Server '$PostgreSQLServerName' is in unexpected state '$($server.State)'. Skipping startup."
    }
}

Write-Output "PostgreSQL startup process completed!."

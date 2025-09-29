param (
    [string]$SubscriptionId,
    [string]$ResourceGroupName,
    [string]$VMName,
    [string]$ScriptDir,
    [string]$PostgreSQLName,
    [string]$PostgresHost,
    [string]$ProjectId = "",
    [int]$TimedMinutes = 60,
    [int]$PostgresPort = 5432,
    [bool]$ShutdownPostgres = $true
)

# Connection account
Connect-AzAccount -Identity
Set-AzContext -SubscriptionId $SubscriptionId

# Ensure Az.PostgreSql module is available
$module = Get-Module -ListAvailable -Name Az.PostgreSql
if (-not $module) {
    Write-Output "Az.PostgreSql module is missing. Installing..."
    Install-Module Az.PostgreSql -Force
}

# Import the module to ensure it's loaded in the session
Import-Module Az.PostgreSql

# Check PostgreSQL server state and start if needed
Write-Output "Checking state of PostgreSQL Server: $PostgreSQLName"
$server = Get-AzPostgreSqlFlexibleServer -ResourceGroupName $ResourceGroupName -Name $PostgreSQLName

if ($server -eq $null) {
    throw "ERROR: PostgreSQL Server '$PostgreSQLName' not found."
}

switch ($server.State) {
    "Ready" {
        Write-Output "INFO: PostgreSQL Server '$PostgreSQLName' is already running. No action needed."
    }
    "Stopped" {
        Write-Output "PostgreSQL Server '$PostgreSQLName' is stopped. Starting..."
        Start-AzPostgreSqlFlexibleServer -ResourceGroupName $ResourceGroupName -Name $PostgreSQLName
    }
    "Starting" {
        Write-Output "WARNING: PostgreSQL Server '$PostgreSQLName' is already starting. Waiting..."
    }
    default {
        Write-Output "WARNING: PostgreSQL Server '$PostgreSQLName' is in unexpected state '$($server.State)'. Skipping startup."
    }
}

# Start VM if needed
$vmStatus = (Get-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName -Status).Statuses | Where-Object { $_.Code -like "PowerState*" }
$startedVM = $false

if ($vmStatus.Code -eq "PowerState/deallocated") {
    Write-Output "Starting VM..."
    Start-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName
    $startedVM = $true
    Start-Sleep -Seconds 60
}

# Wait for PostgreSQL to be ready
Write-Output "Waiting for PostgreSQL to accept connections..."
$maxRetries = 10
$retryCount = 0
$ready = $false
$checkPostgres = @"
pg_isready -h $PostgresHost -p $PostgresPort -d epic_vector
"@

do {
    $result = Invoke-AzVMRunCommand -ResourceGroupName $ResourceGroupName -VMName $VMName `
        -CommandId 'RunShellScript' -ScriptString $checkPostgres
    $ready = $result.Value[0].Message -match "accepting connections"
    if (-not $ready) {
        Start-Sleep -Seconds 10
        $retryCount++
    }
} while (-not $ready -and $retryCount -lt $maxRetries)

if (-not $ready) {
    throw "PostgreSQL did not start in time."
}

# Build dynamic argument string
$argList = ""
if ($TimedMinutes -gt 0) {
    $argList += "--timed $TimedMinutes "
}
if ($ProjectId -ne "") {
    $argList += "--project_id $ProjectId"
}

# Generate timestamped log filename
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = "$ScriptDir/logs/output_$timestamp.log"

# - for 2 step disconnected flow use - then call webhook from script to trigger shutdown etc..
# " nohup python3 -u main.py $argList > $logFile 2>&1 & "

# Run embedder script
Write-Output "Running embedder script..."
$runScript = @"
sudo -u azureuser-vm-embedder bash -c '
mkdir -p $ScriptDir/logs
cd $ScriptDir
source venv/bin/activate
python3 -u main.py $argList > $logFile 2>&1
'
"@
Invoke-AzVMRunCommand -ResourceGroupName $ResourceGroupName -VMName $VMName `
    -CommandId 'RunShellScript' -ScriptString $runScript

# Optionally shut down PostgreSQL
if ($ShutdownPostgres) {
    Write-Output "Shutting down PostgreSQL Server '$PostgreSQLName'..."
    Stop-AzPostgreSqlFlexibleServer -ResourceGroupName $ResourceGroupName -Name $PostgreSQLName
    Write-Output "PostgreSQL Server '$PostgreSQLName' has been stopped."
}

# Deallocate VM if we started it
if ($startedVM) {
    Write-Output "Deallocating VM..."
    Stop-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName -Force
}
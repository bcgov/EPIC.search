param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('dev', 'test', 'prod')]
    [string]$Environment,
    
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "canadacentral",
    
    [Parameter(Mandatory=$true)]
    [SecureString]$AdminPassword,
    
    [Parameter(Mandatory=$false)]
    [switch]$WhatIf
)

# Ensure we're logged in
$context = Get-AzContext
if (!$context) {
    Write-Host "Not logged in. Please run Connect-AzAccount first."
    exit
}

# Check if the resource group exists, create it if it doesn't
$rg = Get-AzResourceGroup -Name $ResourceGroupName -ErrorAction SilentlyContinue
if (!$rg) {
    Write-Host "Resource group $ResourceGroupName does not exist. Creating it..."
    New-AzResourceGroup -Name $ResourceGroupName -Location $Location
    Write-Host "Resource group $ResourceGroupName created."
}

# Set up the deployment parameters
$deploymentParams = @{
    ResourceGroupName = $ResourceGroupName
    TemplateFile      = "$PSScriptRoot\main.bicep"
    TemplateParameterObject = @{
        environment = $Environment
        location    = $Location
        adminPassword = $AdminPassword
    }
}

if ($WhatIf) {
    # Perform what-if deployment to see what would change
    Write-Host "Performing what-if deployment to see what would change..."
    $result = Get-AzResourceGroupDeploymentWhatIfResult @deploymentParams
    Write-Output $result
} else {
    # Deploy the Bicep template
    Write-Host "Starting deployment of $Environment environment to $ResourceGroupName..."
    Write-Host "Private DNS zone integration will be automatically skipped."
    
    $deployment = New-AzResourceGroupDeployment @deploymentParams -Verbose
    
    # Output deployment results
    if ($deployment.ProvisioningState -eq "Succeeded") {
        Write-Host "Deployment succeeded!"
        Write-Host "VNet Name: $($deployment.Outputs.vnetName.Value)"
        Write-Host "VNet ID: $($deployment.Outputs.vnetId.Value)"
        Write-Host "Subnets: $($deployment.Outputs.subnetIds.Value | ConvertTo-Json -Depth 10)"
        Write-Host "PostgreSQL Server: $($deployment.Outputs.postgresqlServerName.Value)"
        Write-Host "PostgreSQL FQDN: $($deployment.Outputs.postgresqlServerFqdn.Value)"
    } else {
        Write-Error "Deployment failed: $($deployment.Error)"
    }
}
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('dev', 'test', 'prod')]
    [string]$Environment,
    
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "canadacentral",
    
    [Parameter(Mandatory=$true)]
    [SecureString]$JumpboxAdminPassword,
    
    [Parameter(Mandatory=$false)]
    [string]$JumpboxCommandToExecute = "powershell -ExecutionPolicy Unrestricted -File install-tools.ps1",
    
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
    TemplateFile      = "$PSScriptRoot\modules\bastion\main.bicep"
    TemplateParameterFile = "$PSScriptRoot\parameters\$Environment\bastion\parameters.bicep"
    TemplateParameterObject = @{
        jumpboxAdminPassword = $JumpboxAdminPassword
        jumpboxCommandToExecute = $JumpboxCommandToExecute
    }
}

if ($WhatIf) {
    # Perform what-if deployment to see what would change
    Write-Host "Performing what-if deployment to see what would change..."
    $result = Get-AzResourceGroupDeploymentWhatIfResult @deploymentParams
    Write-Output $result
} else {
    # Deploy the Bicep template
    Write-Host "Starting deployment of Bastion resources for $Environment environment to $ResourceGroupName..."
    
    $deployment = New-AzResourceGroupDeployment @deploymentParams -Verbose
    
    # Output deployment results
    if ($deployment.ProvisioningState -eq "Succeeded") {
        Write-Host "Deployment succeeded!"
        Write-Host "Bastion Name: $($deployment.Outputs.bastionName.Value)"
        Write-Host "Jumpbox VM Name: $($deployment.Outputs.jumpboxName.Value)"
        Write-Host "Jumpbox Private IP: $($deployment.Outputs.jumpboxPrivateIp.Value)"
    } else {
        Write-Error "Deployment failed: $($deployment.Error)"
    }
}
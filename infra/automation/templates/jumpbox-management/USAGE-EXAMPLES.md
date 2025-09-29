# Jumpbox Management - Usage Examples

## Quick Deploy Examples

### Windows Jumpbox (Basic)

```powershell
.\Deploy-JumpboxVM.ps1 `
    -SubscriptionId "your-subscription-id" `
    -ResourceGroupName "rg-your-troubleshooting" `
    -Location "Canada Central" `
    -VNetName "vnet-your-main" `
    -VNetResourceGroupName "rg-your-network" `
    -SubnetName "snet-internal" `
    -AdminPasswordOrKey (Read-Host -AsSecureString "Enter admin password")
```

### Linux Jumpbox (Custom Configuration)

```powershell
.\Deploy-JumpboxVM.ps1 `
    -SubscriptionId "your-subscription-id" `
    -ResourceGroupName "rg-your-troubleshooting" `
    -Location "Canada Central" `
    -VNetName "vnet-your-main" `
    -VNetResourceGroupName "rg-your-network" `
    -SubnetName "snet-internal" `
    -VMName "vm-jumpbox-linux" `
    -OSType "Linux" `
    -VMSize "Standard_B2ms" `
    -AdminPasswordOrKey (Read-Host -AsSecureString "Enter admin password")
```

## Quick Delete Examples

### Delete Default Jumpbox

```powershell
.\Delete-JumpboxVM.ps1 `
    -SubscriptionId "your-subscription-id" `
    -ResourceGroupName "rg-your-troubleshooting"
```

### Delete Custom Named Jumpbox

```powershell
.\Delete-JumpboxVM.ps1 `
    -SubscriptionId "your-subscription-id" `
    -ResourceGroupName "rg-your-troubleshooting" `
    -VMName "vm-jumpbox-linux"
```

## Troubleshooting Workflow

### 1. Deploy Jumpbox

```powershell
# Replace with your actual values
$subscriptionId = "your-subscription-id"
$resourceGroup = "rg-your-troubleshooting" 
$vnetName = "vnet-your-main"
$vnetResourceGroup = "rg-your-network"
$subnetName = "snet-internal"

.\Deploy-JumpboxVM.ps1 `
    -SubscriptionId $subscriptionId `
    -ResourceGroupName $resourceGroup `
    -Location "Canada Central" `
    -VNetName $vnetName `
    -VNetResourceGroupName $vnetResourceGroup `
    -SubnetName $subnetName `
    -AdminPasswordOrKey (Read-Host -AsSecureString "Enter admin password")
```

### 2. Connect via Bastion

- Navigate to the VM in Azure Portal
- Click "Connect" -> "Bastion"
- Enter credentials and connect

### 3. Perform Troubleshooting

- Network connectivity tests
- DNS resolution checks
- Application debugging
- Log analysis

### 4. Clean Up

```powershell
.\Delete-JumpboxVM.ps1 `
    -SubscriptionId $subscriptionId `
    -ResourceGroupName $resourceGroup
```

## Parameter Reference Templates

### Minimal Windows Deployment

```powershell
$params = @{
    SubscriptionId = "12345678-1234-1234-1234-123456789012"
    ResourceGroupName = "rg-myproject-troubleshooting"
    Location = "Canada Central"
    VNetName = "vnet-myproject-main"
    VNetResourceGroupName = "rg-myproject-network"
    SubnetName = "snet-internal"
    AdminPasswordOrKey = (Read-Host -AsSecureString "Password")
}
.\Deploy-JumpboxVM.ps1 @params
```

### Full Linux Deployment

```powershell
$params = @{
    SubscriptionId = "12345678-1234-1234-1234-123456789012"
    ResourceGroupName = "rg-myproject-troubleshooting"
    Location = "Canada Central"
    VNetName = "vnet-myproject-main"
    VNetResourceGroupName = "rg-myproject-network"
    SubnetName = "snet-internal"
    VMName = "vm-jumpbox-prod"
    VMSize = "Standard_D2s_v3"
    AdminUsername = "azureuser"
    OSType = "Linux"
    AdminPasswordOrKey = (Read-Host -AsSecureString "Password")
}
.\Deploy-JumpboxVM.ps1 @params
```

// Parameters for Bastion deployment in test environment
param environment string = 'test'
param location string = 'canadacentral'
param billingGroup string = 'c4b0a8'

// Additional tags for bastion resources
param tags object = {
  Application: 'epic-search'
}

// VNet and subnet references
param vnetId string = '/subscriptions/7897ceb1-9a86-4639-87d7-7f9ff67142b3/resourceGroups/c4b0a8-test-networking/providers/Microsoft.Network/virtualNetworks/c4b0a8-test-vwan-spoke'

// VNet and subnet names will be constructed from the IDs
var serversSubnetId = '${vnetId}/subnets/snet-servers'

// Bastion config
param bastionName string = 'bastion-test'
param bastionNsgName string = 'nsg-bastion'

// Jumpbox VM config
param jumpboxName string = 'vm-jumpbox-test'
param jumpboxSize string = 'Standard_B2s'
param jumpboxAdminUsername string = 'c4b0a8-test-jumpbox'

// Auto-shutdown settings
param enableJumpboxAutoShutdown bool = true
param jumpboxShutdownTime string = '1900'
param timeZone string = 'Pacific Standard Time'

// Parameters are exported to be used in deploy-bastion.ps1
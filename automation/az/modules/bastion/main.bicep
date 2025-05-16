@description('Environment name: dev, test, or prod')
param environment string

@description('Location for all resources')
param location string = resourceGroup().location

@description('Project or billing group tag')
param billingGroup string

@description('Additional tags to apply to resources')
param tags object = {}

@description('Name for the Bastion host')
param bastionName string = 'bastion-${environment}'

@description('Name for the jumpbox VM')
param jumpboxName string = 'vm-jumpbox-${environment}'

@description('Jumpbox admin username')
param jumpboxAdminUsername string = '${billingGroup}-${environment}-jumpbox'

@description('Jumpbox admin password')
@secure()
param jumpboxAdminPassword string

@description('Size for the jumpbox VM')
param jumpboxSize string = 'Standard_B2s'

@description('Network Security Group name for the bastion subnet')
param bastionNsgName string = 'nsg-bastion'

@description('Resource ID of the VNet containing the AzureBastionSubnet')
param vnetId string

@description('Resource ID of the servers subnet for jumpbox deployment')
param serversSubnetId string

@description('Command to execute for installing tools on the jumpbox VM')
@secure()
param jumpboxCommandToExecute string = 'powershell -ExecutionPolicy Unrestricted -File install-tools.ps1'

@description('Set to true to enable auto-shutdown of the jumpbox VM')
param enableJumpboxAutoShutdown bool = true

@description('Time to auto-shutdown jumpbox VM (24 hour format)')
param jumpboxShutdownTime string = '1900'

@description('Time zone for auto-shutdown schedule')
param timeZone string = 'Pacific Standard Time'

// Define common tags
var commonTags = union({
  environment: environment
  billing_group: billingGroup
  ministry_name: 'EAO'
  account_coding: '1152990370037633129L0122'
}, tags)

// Extract VNet name from resource ID
var vnetResourceId = split(vnetId, '/')
var vnetName = last(split(vnetId, '/'))

// Extract subnet names from VNet ID
var bastionSubnetName = 'AzureBastionSubnet'
var serversSubnetName = last(split(serversSubnetId, '/'))

// Public IP address name for Bastion host
var bastionPipName = '${bastionName}-${uniqueString(resourceGroup().id)}-pip'

// Deploy NSG for Bastion subnet
module bastionNsg 'nsg.bicep' = {
  name: 'bastion-nsg-deployment'
  params: {
    location: location
    nsgName: bastionNsgName
    tags: commonTags
  }
}

// Create public IP for Bastion host
resource bastionPublicIp 'Microsoft.Network/publicIPAddresses@2023-09-01' = {
  name: bastionPipName
  location: location
  tags: commonTags
  sku: {
    name: 'Standard'
    tier: 'Regional'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
    publicIPAddressVersion: 'IPv4'
    idleTimeoutInMinutes: 4
    ddosSettings: {
      protectionMode: 'VirtualNetworkInherited'
    }
  }
}

// Deploy Bastion host
resource bastionHost 'Microsoft.Network/bastionHosts@2023-09-01' = {
  name: bastionName
  location: location
  tags: commonTags
  sku: {
    name: 'Developer'
  }
  properties: {
    scaleUnits: 2
    virtualNetwork: {
      id: vnetId
    }
    ipConfigurations: [
      {
        name: 'IpConf'
        properties: {
          publicIPAddress: {
            id: bastionPublicIp.id
          }
          subnet: {
            id: '${vnetId}/subnets/${bastionSubnetName}'
          }
        }
      }
    ]
  }
}

// Create NIC for jumpbox VM
resource jumpboxNic 'Microsoft.Network/networkInterfaces@2023-09-01' = {
  name: '${jumpboxName}-nic'
  location: location
  tags: commonTags
  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          privateIPAllocationMethod: 'Dynamic'
          subnet: {
            id: serversSubnetId
          }
          primary: true
          privateIPAddressVersion: 'IPv4'
        }
      }
    ]
    enableAcceleratedNetworking: false
    enableIPForwarding: false
    nicType: 'Standard'
  }
}

// Deploy jumpbox VM
resource jumpboxVm 'Microsoft.Compute/virtualMachines@2023-09-01' = {
  name: jumpboxName
  location: location
  tags: commonTags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    hardwareProfile: {
      vmSize: jumpboxSize
    }
    storageProfile: {
      imageReference: {
        publisher: 'MicrosoftWindowsServer'
        offer: 'WindowsServer'
        sku: '2022-datacenter-azure-edition'
        version: 'latest'
      }
      osDisk: {
        createOption: 'FromImage'
        caching: 'ReadWrite'
        deleteOption: 'Detach'
      }
      dataDisks: []
    }
    osProfile: {
      computerName: jumpboxName
      adminUsername: jumpboxAdminUsername
      adminPassword: jumpboxAdminPassword
      windowsConfiguration: {
        provisionVMAgent: true
        enableAutomaticUpdates: true
        patchSettings: {
          patchMode: 'AutomaticByOS'
          assessmentMode: 'ImageDefault'
        }
      }
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: jumpboxNic.id
          properties: {
            deleteOption: 'Detach'
          }
        }
      ]
    }
  }
}

// Install tools on jumpbox VM
resource jumpboxExtension 'Microsoft.Compute/virtualMachines/extensions@2023-09-01' = {
  parent: jumpboxVm
  name: 'InstallTools'
  location: location
  tags: commonTags
  properties: {
    publisher: 'Microsoft.Compute'
    type: 'CustomScriptExtension'
    typeHandlerVersion: '1.10'
    autoUpgradeMinorVersion: true
    settings: {
      fileUris: [
        'https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/demos/vm-to-vm-throughput-meter-multithreaded/install-tools.ps1'
      ]
    }
    protectedSettings: {
      commandToExecute: jumpboxCommandToExecute
    }
  }
}

// Configure auto-shutdown for jumpbox VM
resource autoShutdown 'Microsoft.DevTestLab/schedules@2018-09-15' = if (enableJumpboxAutoShutdown) {
  name: 'shutdown-computevm-${jumpboxName}'
  location: location
  tags: commonTags
  properties: {
    status: 'Enabled'
    taskType: 'ComputeVmShutdownTask'
    dailyRecurrence: {
      time: jumpboxShutdownTime
    }
    timeZoneId: timeZone
    notificationSettings: {
      status: 'Disabled'
      timeInMinutes: 30
      notificationLocale: 'en'
    }
    targetResourceId: jumpboxVm.id
  }
}

// Create DDoS Alert for the public IP
resource ddosAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${bastionPipName}-DDOS_Attack'
  location: 'global'
  tags: union(commonTags, {
    _deployed_by_amba: 'True'
  })
  properties: {
    description: 'Metric Alert for Public IP Address Under Attack'
    severity: 1
    enabled: true
    scopes: [
      bastionPublicIp.id
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'ifunderddosattack'
          metricNamespace: 'Microsoft.Network/publicIPAddresses'
          metricName: 'ifunderddosattack'
          operator: 'GreaterThan'
          threshold: 0
          timeAggregation: 'Maximum'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    autoMitigate: true
    actions: []
  }
}

// Create VIP Availability Alert for the public IP
resource vipAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${bastionPipName}-VIPAvailabityAlert'
  location: 'global'
  tags: union(commonTags, {
    _deployed_by_amba: 'True'
  })
  properties: {
    description: 'Metric Alert for Public IP Address VIP Availability'
    severity: 1
    enabled: true
    scopes: [
      bastionPublicIp.id
    ]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'VipAvailability'
          metricNamespace: 'Microsoft.Network/publicIPAddresses'
          metricName: 'VipAvailability'
          operator: 'LessThan'
          threshold: 1
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    autoMitigate: true
    actions: []
  }
}

// Outputs
output bastionId string = bastionHost.id
output bastionName string = bastionHost.name
output jumpboxId string = jumpboxVm.id
output jumpboxName string = jumpboxVm.name
output jumpboxPrivateIp string = jumpboxNic.properties.ipConfigurations[0].properties.privateIPAddress
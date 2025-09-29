# VM Start/Stop Automation

This directory contains automation components for starting and stopping Azure Virtual Machines on a schedule. The runbooks support multiple VMs per execution and include proper error handling and status checking.

## Files Overview

- **`deploy-vm-runbooks.bicep`** - Bicep template to deploy Start-VMs and Stop-VMs runbooks
- **`Start-VMs.ps1`** - PowerShell runbook to start multiple VMs
- **`Stop-VMs.ps1`** - PowerShell runbook to stop (deallocate) multiple VMs
- **`publish-runbooks.ps1`** - Script to publish runbooks to Automation Account
- **`Assign-VMRoles.ps1`** - Script to assign Virtual Machine Contributor role to VMs
- **`link-vm-start-morning.json`** - Schedule link parameters for morning VM startup
- **`link-vm-stop-evening.json`** - Schedule link parameters for evening VM shutdown

## Required Permissions

The managed identity running these runbooks needs:

- **Virtual Machine Contributor** role on target VMs or resource groups containing VMs

## Runbook Features

### Start-VMs.ps1

- Starts multiple VMs specified in comma-separated list
- Checks current power state before attempting start
- Skips VMs that are already running or starting
- Uses async operations for faster execution
- Includes error handling for missing VMs

### Stop-VMs.ps1

- Stops (deallocates) multiple VMs to save costs
- Checks current power state before attempting stop
- Skips VMs that are already deallocated or deallocating
- Uses async operations for faster execution
- Force stops VMs without waiting for graceful shutdown

## Parameters

### Required Parameters

- **SubscriptionId** - Azure subscription ID containing the VMs
- **ResourceGroupName** - Resource group containing the VMs
- **VMNames** - Comma-separated list of VM names (e.g., "vm1,vm2,vm3")

### VM Names Format

The `VMNames` parameter accepts:

- Single VM: `"vm-web-01"`
- Multiple VMs: `"vm-web-01,vm-web-02,vm-db-01"`
- Spaces are automatically trimmed: `"vm1, vm2, vm3"` works fine

## Usage Pattern

### 1. Deploy the runbooks

```bash
az deployment group create \
  --resource-group rg-your-automation \
  --template-file deploy-vm-runbooks.bicep \
  --parameters automationAccountName=auto-your-account
```

### 2. Assign IAM roles

```powershell
.\Assign-VMRoles.ps1 -PrincipalId <managed-identity-id> -ResourceGroupName "rg-your-vms"
```

### 3. Link to schedules

```bash
# Link Start-VMs to morning schedule
az deployment group create \
  --resource-group rg-your-automation \
  --template-file ../templates/job-schedule-template.bicep \
  --parameters @link-vm-start-morning.json

# Link Stop-VMs to evening schedule  
az deployment group create \
  --resource-group rg-your-automation \
  --template-file ../templates/job-schedule-template.bicep \
  --parameters @link-vm-stop-evening.json
```

## Schedule Integration

The VM automation integrates with your existing weekly schedules:

- **Morning Start**: Links to `MorningStart-Weekdays` schedule (8 AM PST, Monday-Friday)
- **Evening Stop**: Links to `EveningStop-Weekdays` schedule (6 PM PST, Monday-Friday)

## Configuration Examples

### Basic VM Group

Update `link-vm-start-morning.json` and `link-vm-stop-evening.json`:

```json
"runbookParameters": {
  "value": {
    "SubscriptionId": "12345678-1234-1234-1234-123456789012",
    "ResourceGroupName": "rg-myproject-vms",
    "VMNames": "vm-web-01,vm-web-02,vm-api-01"
  }
}
```

### Tag-Based IAM Assignment

```powershell
# Assign roles only to VMs with specific tags
.\Assign-VMRoles.ps1 \
  -PrincipalId "12345678-1234-1234-1234-123456789012" \
  -ResourceGroupName "rg-myproject-vms" \
  -TagName "AutoStartStop" \
  -TagValue "Enabled"
```

### Manual Testing

```powershell
# Test starting VMs manually
Start-AzAutomationRunbook \
  -AutomationAccountName "auto-myproject-tools" \
  -Name "Start-VMs" \
  -ResourceGroupName "rg-myproject-automation" \
  -Parameters @{
    SubscriptionId = "12345678-1234-1234-1234-123456789012"
    ResourceGroupName = "rg-myproject-vms"
    VMNames = "vm-test-01,vm-test-02"
  }
```

## Cost Optimization

### VM Stop Behavior

- Uses `Stop-AzVM -Force` for immediate deallocation
- Deallocated VMs do not incur compute charges
- Storage charges continue for attached disks
- Network resources (NICs, Public IPs) may continue to incur charges

### Best Practices

1. **Use consistent naming** for VMs that should be managed together
2. **Tag VMs appropriately** for easy identification and role assignment
3. **Monitor costs** after implementing automation to verify savings
4. **Test schedules** in non-production environments first
5. **Document VM dependencies** that might be affected by start/stop schedules

## Troubleshooting

### Common Issues

- **Permission denied**: Ensure managed identity has Virtual Machine Contributor role
- **VM not found**: Check VM names and resource group names in parameters
- **Timeout errors**: Large numbers of VMs may take time to start/stop

### Monitoring

- Check Automation Account job history for execution results
- Use Azure Monitor to track VM power state changes
- Set up alerts for failed runbook executions

## Integration with Other Services

### Dependencies

- VMs may have dependencies on databases, storage accounts, or other services
- Consider the startup/shutdown order when VMs depend on each other
- Test application connectivity after automated restarts

### Complementary Automation

- Combine with App Services start/stop for full environment management  
- Integrate with PostgreSQL start/stop for complete cost optimization
- Use with monitoring automation to verify service health after startup

## Future Enhancements

Potential improvements for this automation:

- **Health checks** after VM startup to verify readiness
- **Dependency ordering** for VMs that must start in sequence
- **Integration with load balancers** to manage traffic during restarts
- **Notification system** for start/stop completion
- **Cost reporting** integration to track savings

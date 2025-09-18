# Teardown and End-to-End Testing Guide

This guide provides step-by-step instructions for tearing down the existing automation infrastructure and testing the updated modular deployment.

## 🔥 Complete Teardown

### 1. Check Current Resources

First, verify what exists in your environment:

```bash
# List automation accounts in the subscription
az automation account list --query "[].{Name:name, ResourceGroup:resourceGroup, Location:location}" --output table

# Check role assignments for the automation account (get Principal ID first)
az automation account show \
  --automation-account-name "auto-myproject-tools" \
  --resource-group "rg-tools-automation" \
  --query "identity.principalId" --output tsv

# List role assignments for the managed identity (replace with actual Principal ID)
az role assignment list \
  --assignee "YOUR_PRINCIPAL_ID_HERE" \
  --query "[].{PrincipalId:principalId, RoleDefinitionName:roleDefinitionName, Scope:scope}" \
  --output table
```

### 2. Remove Role Assignments (Optional - See Note Below)

**📝 Note**: If you're deleting the entire resource group (Step 3), role assignments are automatically cleaned up when the automation account is deleted. You only need to manually remove role assignments if:

- You want to keep the automation account but remove specific permissions
- You're deleting the automation account individually (not the whole resource group)

**Manual Role Assignment Removal (if needed):**

```bash
# Get the Principal ID of your automation account (optional step)
PRINCIPAL_ID=$(az automation account show \
  --automation-account-name "auto-myproject-tools" \
  --resource-group "rg-tools-automation" \
  --query "identity.principalId" --output tsv)

echo "Principal ID: $PRINCIPAL_ID"

# List all role assignments for this principal (optional verification)
az role assignment list --assignee $PRINCIPAL_ID --output table

# Remove specific role assignments (only if keeping the automation account)
az role assignment delete \
  --assignee $PRINCIPAL_ID \
  --role "Website Contributor" \
  --resource-group "rg-your-app-services"
```

### 3. Delete Resource Group (Recommended - Cleans Everything)

**✅ Recommended Approach**: Delete the entire resource group for complete cleanup.

```bash
# Delete the entire automation resource group (this automatically removes role assignments)
az group delete \
  --name "rg-tools-automation" \
  --yes \
  --no-wait

# Monitor deletion progress
az group show --name "rg-tools-automation" --query "properties.provisioningState" --output tsv
```

**Why this approach is better:**

- ✅ Automatically removes all role assignments (no orphaned assignments)
- ✅ Cleans up all resources in one command
- ✅ No manual role assignment cleanup needed
- ✅ Faster and more reliable

## 🚀 End-to-End Testing

### Phase 1: Core Infrastructure Deployment

Test the updated modular infrastructure:

```bash
# Deploy core automation infrastructure (NO runbooks)
az deployment sub create \
  --location "East US" \
  --template-file deploy-subscription.bicep \
  --parameters @deploy-subscription.bicepparam \
  --confirm-with-what-if

# Verify deployment
az automation account show \
  --automation-account-name "auto-myproject-tools" \
  --resource-group "rg-tools-automation" \
  --query "{Name:name, State:state, Identity:identity.type}" --output table

# Check that NO runbooks are deployed (should be empty)
az automation runbook list \
  --automation-account-name "auto-myproject-tools" \
  --resource-group "rg-tools-automation" \
  --query "[].name" --output table
```

### Phase 2: Template-Based Runbook Deployment

Test the new templates-based approach:

```bash
# Deploy App Service start/stop runbooks using template
az deployment group create \
  --resource-group "rg-tools-automation" \
  --template-file templates/start-stop-appservices/deploy-appservice-runbooks.bicep \
  --parameters automationAccountName="auto-myproject-tools" \
  --confirm-with-what-if

# Verify runbooks are created
az automation runbook list \
  --automation-account-name "auto-myproject-tools" \
  --resource-group "rg-tools-automation" \
  --query "[].{Name:name, Type:runbookType, State:state}" --output table

# Expected output: Start-AppServices and Stop-AppServices runbooks
```

### Phase 3: Schedule Creation Testing

Test schedule and job-schedule templates:

```bash
# Create a test schedule (8 AM PST = 4 PM UTC)
az deployment group create \
  --resource-group "rg-tools-automation" \
  --template-file templates/schedule-template.bicep \
  --parameters automationAccountName="auto-myproject-tools" \
    scheduleName="BusinessHours-Start" \
    scheduleDescription="Start services at 8 AM PST" \
    startTime="2025-09-19T16:00:00Z" \
    frequency="Daily" \
    interval=1 \
    timeZone="Pacific Standard Time"

# Create stop schedule (5 PM PST = 1 AM UTC next day)
az deployment group create \
  --resource-group "rg-tools-automation" \
  --template-file templates/schedule-template.bicep \
  --parameters automationAccountName="auto-myproject-tools" \
    scheduleName="BusinessHours-Stop" \
    scheduleDescription="Stop services at 5 PM PST" \
    startTime="2025-09-20T01:00:00Z" \
    frequency="Daily" \
    interval=1 \
    timeZone="Pacific Standard Time"

# Verify schedules
az automation schedule list \
  --automation-account-name "auto-myproject-tools" \
  --resource-group "rg-tools-automation" \
  --query "[].{Name:name, StartTime:startTime, Frequency:frequency}" --output table
```

### Phase 4: Job Schedule Linking

Link runbooks to schedules:

```bash
# Link Start-AppServices to start schedule
az deployment group create \
  --resource-group "rg-tools-automation" \
  --template-file templates/job-schedule-template.bicep \
  --parameters automationAccountName="auto-myproject-tools" \
    runbookName="Start-AppServices" \
    scheduleName="BusinessHours-Start"

# Link Stop-AppServices to stop schedule
az deployment group create \
  --resource-group "rg-tools-automation" \
  --template-file templates/job-schedule-template.bicep \
  --parameters automationAccountName="auto-myproject-tools" \
    runbookName="Stop-AppServices" \
    scheduleName="BusinessHours-Stop"

# Verify job schedules (there's no direct Azure CLI command, use portal or REST API)
echo "Check job schedules in Azure Portal: Automation Account > Schedule > Runbooks"
```

### Phase 5: IAM Assignment Testing

Test cross-subscription role assignments:

```bash
# Get automation account principal ID
PRINCIPAL_ID=$(az automation account show \
  --automation-account-name "auto-myproject-tools" \
  --resource-group "rg-tools-automation" \
  --query "identity.principalId" --output tsv)

echo "Automation Account Principal ID: $PRINCIPAL_ID"

# Assign Website Contributor role to App Service resource group(s)
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Website Contributor" \
  --resource-group "rg-your-app-services"

# Verify role assignment
az role assignment list \
  --assignee $PRINCIPAL_ID \
  --query "[].{Role:roleDefinitionName, Scope:scope}" --output table
```

## ✅ Validation Checklist

After completing all phases, verify:

- [ ] **Core Infrastructure**: Automation account deployed without any runbooks
- [ ] **Modular Structure**: Files organized in `modules/`, `templates/`, `docs/` folders
- [ ] **Template Deployment**: Runbooks deployed only via templates, not core infrastructure
- [ ] **Schedule Creation**: Both start and stop schedules created with correct times
- [ ] **Job Linking**: Runbooks linked to schedules successfully
- [ ] **IAM Permissions**: Managed identity has appropriate permissions to target resources
- [ ] **No Orphaned Resources**: Clean teardown with no leftover role assignments

## 🔧 Troubleshooting

### Common Issues

1. **Role assignment errors**: ✅ **SOLVED** - When deleting the resource group, role assignments are automatically cleaned up
2. **Schedule time zones**: Use proper time zone names (e.g., "Pacific Standard Time", not "PST")
3. **Template references**: Ensure all Bicep files reference modules from correct paths
4. **Parameter mismatches**: Verify parameter files don't reference removed parameters

### Key Insights

- **Managed Identity Cleanup**: System-assigned managed identities are automatically cleaned up when the parent resource (automation account) is deleted
- **Resource Group Deletion**: Deleting the resource group is the cleanest approach - it removes all resources and their associated role assignments
- **No Manual Cleanup**: You don't need to manually remove role assignments if you're deleting the entire resource group

### Useful Commands

```bash
# Check deployment operations
az deployment group list --resource-group "rg-tools-automation" --query "[].{Name:name, State:properties.provisioningState}" --output table

# Get detailed error information
az deployment group show --resource-group "rg-tools-automation" --name "DEPLOYMENT_NAME" --query "properties.error"

# List all resources in the automation resource group
az resource list --resource-group "rg-tools-automation" --output table
```

## 📖 Documentation References

- [Scheduling Guide](./docs/SCHEDULING.md) - Time zones and scheduling patterns
- [IAM Guide](./docs/APP-SERVICE-IAM.md) - Cross-subscription permissions
- [Main README](./README.md) - Architecture and extension guide

# Azure Automation Infrastructure

This solution provides Infrastructure as Code templates for deploying an Azure Automation Account with extensible runbook support. The core infrastructure is minimal and secure, with optional runbooks and schedules available via templates.

## 🎯 Features

- **Azure Automation Account** with system-assigned managed identity
- **Modular template architecture** for extensible runbook deployment
- **IAM role assignments** for secure resource management
- **Source-controlled runbooks** stored in Git
- **Cross-resource group support** for resources in different RGs
- **Built-in scheduling templates** for automation tasks
- **Security-focused design** with least-privilege access

## 📁 Architecture

### Core Components (Always Deployed)
- **Azure Automation Account**: PowerShell 7.2 runtime with managed identity
- **Role Assignments**: Secure access to specified resource groups
- **Network Security Group**: Bastion host protection (if using bastion module)

### Optional Components (Deploy via Templates)
- **Runbooks**: PowerShell scripts for automation tasks
- **Schedules**: Time-based triggers for runbook execution
- **Job Schedules**: Links between runbooks and schedules

## 📁 File Structure

```text
automation/
├── main.bicep                    # Core infrastructure orchestration
├── main.bicepparam              # Core deployment parameters
├── deploy-subscription.bicep    # Subscription-level deployment (creates RG)
├── deploy-subscription.bicepparam # Parameters for subscription deployment
├── modules/                     # Reusable Bicep modules
│   ├── automation-account.bicep # Automation account with managed identity
│   ├── iam-assignment.bicep     # Role-based access control
│   └── runbook.bicep           # Individual runbook deployment
├── templates/                   # Optional deployments and extensions
│   ├── runbook-template.bicep   # Template for deploying new runbooks
│   ├── schedule-template.bicep  # Template for creating schedules
│   ├── job-schedule-template.bicep # Template for linking runbooks to schedules
│   └── start-stop-appservices/  # App Services automation example
│       ├── deploy-appservice-runbooks.bicep # Deploy start/stop runbooks
│       ├── Start-AppServices.ps1 # PowerShell script to start App Services
│       └── Stop-AppServices.ps1 # PowerShell script to stop App Services
├── bastion/                     # Network security components
│   └── nsg.bicep               # Network Security Group for Bastion
├── docs/                       # Documentation
│   ├── APP-SERVICE-IAM.md      # Cross-subscription IAM guide
│   └── SCHEDULING.md           # Scheduling and automation guide
└── README.md                   # This file
```

## 🚀 Quick Start

### 1. Deploy Core Infrastructure

The core infrastructure includes only the Azure Automation Account, managed identity, and IAM permissions. Runbooks are deployed separately via templates.

```bash
# Deploy to subscription (creates resource group + automation account)
az deployment sub create \
  --location "East US" \
  --template-file deploy-subscription.bicep \
  --parameters @deploy-subscription.bicepparam

# OR deploy to existing resource group
az deployment group create \
  --resource-group "rg-automation-dev" \
  --template-file main.bicep \
  --parameters @main.bicepparam
```

### 2. Add Runbooks (Optional)

Use templates to add specific runbooks and automation tasks:

```bash
# Deploy App Service Start/Stop runbooks
az deployment group create \
  --resource-group "rg-automation-dev" \
  --template-file templates/start-stop-appservices/deploy-appservice-runbooks.bicep \
  --parameters automationAccountName="auto-myproject-dev"

# Add your own runbooks using the template
az deployment group create \
  --resource-group "rg-automation-dev" \
  --template-file templates/runbook-template.bicep \
  --parameters automationAccountName="auto-myproject-dev" runbookName="MyCustomRunbook"
```

### 3. Add Schedules (Optional)

Create automated schedules for your runbooks:

```bash
# Create business hours schedule (8 AM - 5 PM PST)
az deployment group create \
  --resource-group "rg-automation-dev" \
  --template-file templates/schedule-template.bicep \
  --parameters automationAccountName="auto-myproject-dev" \
    scheduleName="BusinessHours-Start" \
    startTime="2024-01-01T16:00:00Z" \
    frequency="Daily" \
    interval=1

# Link runbook to schedule
az deployment group create \
  --resource-group "rg-automation-dev" \
  --template-file templates/job-schedule-template.bicep \
  --parameters automationAccountName="auto-myproject-dev" \
    runbookName="Start-AppServices" \
    scheduleName="BusinessHours-Start"
```

### 4. Install PowerShell Modules

After deployment, install required PowerShell modules in the automation account:

**Via Azure Portal (Recommended):**
1. Go to Azure Portal → Automation Account → Modules → Browse Gallery  
2. Search for and install: `Az.Accounts` (install first), then `Az.Websites`
3. Wait for each module to install completely before installing the next

**Via PowerShell (if you have Az.Automation module):**

```powershell
# Install modules via PowerShell (requires Az.Automation module locally)
New-AzAutomationModule -AutomationAccountName "auto-myproject-dev" -ResourceGroupName "rg-automation-dev" -Name "Az.Accounts"
New-AzAutomationModule -AutomationAccountName "auto-myproject-dev" -ResourceGroupName "rg-automation-dev" -Name "Az.Websites"
```

### 5. Upload Runbook Content

If using templates that deploy runbooks, upload the PowerShell script content:

```powershell
# Install Az.Automation module locally (if not already installed)
Install-Module -Name Az.Automation -Force -AllowClobber

# Connect to Azure (REQUIRED)
Connect-AzAccount

# Upload runbook content (example for App Service runbooks)
Import-AzAutomationRunbook \
  -AutomationAccountName "auto-myproject-dev" \
  -ResourceGroupName "rg-automation-dev" \
  -Name "Start-AppServices" \
  -Type PowerShell72 \
  -Path "./templates/start-stop-appservices/Start-AppServices.ps1" \
  -Published \
  -Force

Import-AzAutomationRunbook \
  -AutomationAccountName "auto-myproject-dev" \
  -ResourceGroupName "rg-automation-dev" \
  -Name "Stop-AppServices" \
  -Type PowerShell72 \
  -Path "./templates/start-stop-appservices/Stop-AppServices.ps1" \
  -Published \
  -Force
```

### 6. Assign IAM Permissions (For Cross-Subscription Access)

Use the provided script to assign Website Contributor role to tagged App Services:

```powershell
# Assign permissions to App Services with specific tags
.\scripts\Assign-AppServiceRoles-Clean.ps1 `
  -PrincipalId "your-automation-account-principal-id" `
  -SubscriptionName "target-subscription-name" `
  -ResourceGroupName "target-resource-group" `
  -TagName "automation_target" `
  -TagValue "app_service"
```

**Note**: If you encounter Microsoft Graph authentication errors, run:
```powershell
az logout
az login --scope https://graph.microsoft.com//.default
```

### 7. Create Schedules and Link Runbooks

Create schedules using parameter files:

```powershell
# Create morning start schedule (8 AM PST weekdays)
az deployment group create `
  --resource-group "rg-tools-automation" `
  --template-file templates/schedule-template.bicep `
  --parameters @morning-start-schedule.json

# Create evening stop schedule (5 PM PST weekdays)  
az deployment group create `
  --resource-group "rg-tools-automation" `
  --template-file templates/schedule-template.bicep `
  --parameters @evening-stop-schedule.json

# Link Start-AppServices runbook to morning schedule
az deployment group create `
  --resource-group "rg-tools-automation" `
  --template-file templates/job-schedule-template.bicep `
  --parameters @link-start-morning.json

# Link Stop-AppServices runbook to evening schedule
az deployment group create `
  --resource-group "rg-tools-automation" `
  --template-file templates/job-schedule-template.bicep `
  --parameters @link-stop-evening.json
```

## 🔧 Extending the Solution

This solution is designed for extensibility. Here's how to add new automation capabilities:

### Adding New Runbooks

1. **Create the PowerShell script** in your workspace
2. **Deploy using the runbook template**:

```bash
az deployment group create \
  --resource-group "rg-automation-dev" \
  --template-file templates/runbook-template.bicep \
  --parameters automationAccountName="auto-myproject-dev" \
    runbookName="MyNewRunbook" \
    runbookDescription="Description of what this runbook does" \
    runbookType="PowerShell72"
```

3. **Upload the script content** using PowerShell (see step 5 above)

### Adding Schedules

1. **Create a schedule**:

```bash
az deployment group create \
  --resource-group "rg-automation-dev" \
  --template-file templates/schedule-template.bicep \
  --parameters automationAccountName="auto-myproject-dev" \
    scheduleName="MySchedule" \
    startTime="2024-01-01T09:00:00Z" \
    frequency="Daily" \
    interval=1
```

2. **Link runbook to schedule**:

```bash
az deployment group create \
  --resource-group "rg-automation-dev" \
  --template-file templates/job-schedule-template.bicep \
  --parameters automationAccountName="auto-myproject-dev" \
    runbookName="MyNewRunbook" \
    scheduleName="MySchedule"
```

### Creating Custom Templates

Copy and modify existing templates in the `templates/` directory:

- `templates/runbook-template.bicep` - For new runbook types
- `templates/schedule-template.bicep` - For custom scheduling patterns  
- `templates/job-schedule-template.bicep` - For linking runbooks and schedules

## 📖 Documentation

- **[Tagging Strategy](./docs/TAGGING.md)** - Centralized tagging for compliance and billing
- **[Scheduling Guide](./docs/SCHEDULING.md)** - Creating and managing automated schedules
- **[IAM Guide](./docs/APP-SERVICE-IAM.md)** - Cross-subscription permission setup

## 📋 Parameters

### Core Infrastructure Parameters

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `automationAccountName` | Name of the automation account | - | ✅ |
| `location` | Azure region | Resource group location | ❌ |
| `tags` | Resource tags | `{}` | ❌ |
| `sku` | Automation account SKU (`Free` or `Basic`) | `Basic` | ❌ |
| `appServiceResourceGroups` | Resource groups for IAM permissions | `[]` | ❌ |
| `deployModules` | Deploy PowerShell modules (can be unreliable) | `false` | ❌ |

### Template Parameters

Each template in the `templates/` directory has its own parameters. See the individual template files for specific parameter requirements.

## 🔐 Security Features

- **Managed Identity**: Automation account uses system-assigned managed identity
- **Least Privilege**: Role assignments limited to specified resource groups
- **No Stored Credentials**: All authentication uses Azure AD
- **Cross-Subscription Support**: Can manage resources across subscription boundaries
- **Source Control Integration**: All scripts stored in Git for auditability

## 🚀 Example Use Cases

### Business Hours Automation
- Start App Services at 8 AM PST (4 PM UTC)
- Stop App Services at 5 PM PST (1 AM UTC next day)
- Weekend shutdown Friday 5 PM to Monday 8 AM

### Cost Optimization
- Automated scaling down of non-production environments
- Scheduled shutdown of development resources
- Smart resource management during off-hours

### Operational Tasks
- Automated backup triggers
- Health check runbooks
- Maintenance window automation
- Log cleanup and archival

## � Support

For issues or questions:

1. Check the documentation in the `docs/` folder
2. Review template examples in `templates/`
3. Validate parameter files match your environment
4. Ensure proper IAM permissions are configured

---

**Note**: This solution uses modular architecture. Core infrastructure is deployed separately from runbooks and schedules, allowing for flexible and secure automation management.

## 🛠️ Runbook Parameters

### Start-AppServices / Stop-AppServices

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ResourceGroupName` | String | ✅ | Resource group containing the App Services |
| `AppServiceNames` | String | ✅ | Comma-separated list of App Service names |
| `SubscriptionId` | String | ✅ | Azure subscription ID |
| `WaitForStartup` | Switch | ❌ | Wait for App Services to start (Start only) |
| `WaitForShutdown` | Switch | ❌ | Wait for App Services to stop (Stop only) |

## 🔄 Automation Scenarios

### Scheduled Start/Stop

Create schedules in the automation account:

```powershell
# Create morning start schedule
New-AzAutomationSchedule \
  -AutomationAccountName "auto-myproject" \
  -ResourceGroupName "rg-myproject-automation" \
  -Name "MorningStart" \
  -StartTime "08:00" \
  -DayInterval 1

# Link runbook to schedule
Register-AzAutomationScheduledRunbook \
  -AutomationAccountName "auto-myproject" \
  -ResourceGroupName "rg-myproject-automation" \
  -RunbookName "Start-AppServices" \
  -ScheduleName "MorningStart" \
  -Parameters @{
    ResourceGroupName = "rg-myproject-apps-dev"
    AppServiceNames = "app1,app2"
    SubscriptionId = "your-subscription-id"
  }
```

## 🚨 Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure the automation account has Website Contributor role on the target resource group
2. **Module Import Errors**: Wait for Az.Websites and Az.Accounts modules to import completely
3. **App Service Not Found**: Verify App Service names and resource group names are correct
4. **Script Timeout**: Use `WaitForStartup`/`WaitForShutdown` parameters for confirmation

### Monitoring

- Check runbook job history in Azure portal
- Review job output and error streams
- Monitor App Service states before and after execution

## 📚 Additional Resources

- [Azure Automation Documentation](https://docs.microsoft.com/en-us/azure/automation/)
- [PowerShell Runbooks](https://docs.microsoft.com/en-us/azure/automation/automation-runbook-types)
- [Managed Identity for Automation](https://docs.microsoft.com/en-us/azure/automation/automation-security-overview#managed-identities)
 
 
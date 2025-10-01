# Azure Automation Infrastructure

This solution provides Infrastructure as Code templates for deploying an Azure Automation Account with extensible runbook support for cross-subscription resource management. The solution includes automated start/stop capabilities for App Services and PostgreSQL Flexible Servers.

## 🚀 Quick Start

For quick deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

For comprehensive setup including runbooks, IAM, and scheduling, continue reading this document.

## 🎯 Features

- **Cross-subscription automation** - Automation account in tools subscription manages resources in dev/test/prod
- **Custom RBAC roles** - Environment-specific custom roles with least-privilege access
- **Modular template architecture** - Reusable templates for different service types
- **Automated scheduling** - Built-in weekday start/stop schedules
- **Parameterized deployments** - Environment-specific configurations
- **Source-controlled runbooks** - All automation scripts stored in Git
- **Security-focused design** - Managed identity with minimal required permissions

## 🏗️ Architecture

### Multi-Subscription Setup

```text
Tools Subscription (c4b0a8-tools)
├── Azure Automation Account (auto-epic-tools)
├── Runbooks (Start/Stop scripts)
└── Schedules (Morning start / Evening stop)

Environment Subscriptions (dev/test/prod)
├── Custom Roles (PostgreSQL Operator - {Environment})
├── Role Assignments (Tools → Environment resources)
├── App Services
└── PostgreSQL Flexible Servers
```

### Core Components

- **Azure Automation Account**: PowerShell 7.2 runtime with system-assigned managed identity
- **Custom Roles**: Environment-specific roles with start/stop permissions
- **Role Assignments**: Cross-subscription permissions for automation account
- **Runbooks**: PowerShell scripts for service management
- **Schedules**: Automated timing for start/stop operations

## 📁 File Structure

```text
automation/
├── main.bicep                          # Core infrastructure orchestration
├── main.bicepparam                     # Core deployment parameters
├── deploy-subscription.bicep           # Subscription-level deployment
├── deploy-subscription.bicepparam      # Subscription deployment parameters
├── shared/
│   ├── tags.bicep                      # Centralized tagging function
│   └── organizational-tags.parameters.json # Organization tag values
├── modules/
│   ├── automation-account.bicep        # Automation account with managed identity
│   ├── iam-assignment.bicep           # Role-based access control
│   ├── runbook.bicep                  # Individual runbook deployment
│   └── postgresql-custom-role.bicep    # PostgreSQL custom role definition
├── templates/
│   ├── runbook-template.bicep          # Template for deploying runbooks
│   ├── schedule-template.bicep         # Template for creating schedules
│   ├── job-schedule-template.bicep     # Template for linking runbooks to schedules
│   ├── start-stop-appservices/         # App Services automation
│   │   ├── deploy-appservice-runbooks.bicep
│   │   ├── publish-runbooks.ps1
│   │   ├── Assign-AppServiceRoles.ps1
│   │   ├── Start-AppServices.ps1
│   │   ├── Stop-AppServices.ps1
│   │   ├── link-start-morning.json
│   │   └── link-stop-evening.json
│   └── start-stop-postgresql/          # PostgreSQL automation
│       ├── deploy-postgresql-customrole.bicep
│       ├── deploy-postgresql-customrole.bicepparam
│       ├── deploy-postgresql-runbooks.bicep
│       ├── publish-runbooks.ps1
│       ├── Assign-PostgreSQLRoles.ps1
│       ├── Start-PostgreSQL.ps1
│       ├── Stop-PostgreSQL.ps1
│       ├── link-postgresql-start-morning.json
│       └── link-postgresql-stop-evening.json
├── morning-start-schedule.json         # Weekday morning schedule definition
├── evening-stop-schedule.json          # Weekday evening schedule definition
└── docs/                              # Additional documentation
```text
├── bastion/                     # Network security components
│   └── nsg.bicep               # Network Security Group for Bastion
├── docs/                       # Documentation
│   ├── APP-SERVICE-IAM.md      # Cross-subscription IAM guide
│   └── SCHEDULING.md           # Scheduling and automation guide
└── README.md                   # This file
```

## 🚀 Complete Setup Guide

### Prerequisites

1. **Azure CLI** installed and logged in
2. **Bicep CLI** (latest version recommended)
3. **PowerShell 7+** for running scripts
4. **Appropriate Azure permissions**:
   - Subscription Owner or Contributor + User Access Administrator
   - Ability to create custom roles and role assignments

### Step 1: Configure Organizational Tags

Edit the organizational tag values for your environment:

```bash
# Edit shared/organizational-tags.parameters.json
{
  "parameters": {
    "accountCoding": {
      "value": "your-account-coding-here"     # Replace with your account coding
    },
    "billingGroup": {
      "value": "your-billing-group-code"     # Replace with your billing group
    },
    "ministryName": {
      "value": "Your Ministry Name"          # Replace with your ministry/org name
    }
  }
}
```

### Step 2: Deploy Core Infrastructure (Tools Subscription)

Deploy the automation account in your tools/shared services subscription:

```bash
# Switch to tools subscription
az account set --subscription "your-tools-subscription"

# Option A: Deploy with new resource group
az deployment sub create \
  --location "Canada Central" \
  --template-file deploy-subscription.bicep \
  --parameters @deploy-subscription.bicepparam

# Option B: Deploy to existing resource group
az deployment group create \
  --resource-group "rg-tools-automation" \
  --template-file main.bicep \
  --parameters @main.bicepparam
```

### Step 3: Deploy and Publish App Services Automation

```bash
# 1. Deploy App Services runbooks
cd templates/start-stop-appservices
az deployment group create \
  --resource-group "rg-tools-automation" \
  --template-file deploy-appservice-runbooks.bicep \
  --parameters automationAccountName="auto-your-automation-account"

# 2. Publish runbook content
.\publish-runbooks.ps1 -AutomationAccountName "auto-your-automation-account" -ResourceGroupName "rg-tools-automation"

# 3. Assign Website Contributor role to App Services (run for each environment)
az account set --subscription "your-target-subscription"
.\Assign-AppServiceRoles.ps1 -PrincipalId "your-automation-principal-id" -ResourceGroupName "rg-your-appservices" -SubscriptionName "your-target-subscription"

# 4. Link to schedules (back in tools subscription)
az account set --subscription "your-tools-subscription"
cd ../../  # Back to automation root
az deployment group create \
  --resource-group "rg-tools-automation" \
  --template-file templates/job-schedule-template.bicep \
  --parameters @templates/start-stop-appservices/link-start-morning.json

az deployment group create \
  --resource-group "rg-tools-automation" \
  --template-file templates/job-schedule-template.bicep \
  --parameters @templates/start-stop-appservices/link-stop-evening.json
```

### Step 4: Deploy and Publish PostgreSQL Automation

```bash
# 1. Deploy PostgreSQL custom role (in each target subscription)
cd templates/start-stop-postgresql
az account set --subscription "your-target-subscription"

# Edit deploy-postgresql-customrole.bicepparam with environment suffix (Dev/Test/Prod)
az deployment sub create \
  --location "Canada Central" \
  --template-file deploy-postgresql-customrole.bicep \
  --parameters @deploy-postgresql-customrole.bicepparam

# 2. Deploy PostgreSQL runbooks (in tools subscription)
az account set --subscription "your-tools-subscription"
az deployment group create \
  --resource-group "rg-tools-automation" \
  --template-file deploy-postgresql-runbooks.bicep \
  --parameters automationAccountName="auto-your-automation-account"

# 3. Publish runbook content
.\publish-runbooks.ps1 -AutomationAccountName "auto-your-automation-account" -ResourceGroupName "rg-tools-automation"

# 4. Assign PostgreSQL custom role (run for each environment)
az account set --subscription "your-target-subscription"
.\Assign-PostgreSQLRoles.ps1 -PrincipalId "your-automation-principal-id" -ResourceGroupName "rg-your-postgresql" -SubscriptionName "your-target-subscription" -EnvironmentSuffix "Dev"

# 5. Link to schedules (back in tools subscription)
az account set --subscription "your-tools-subscription"
cd ../../  # Back to automation root
az deployment group create \
  --resource-group "rg-tools-automation" \
  --template-file templates/job-schedule-template.bicep \
  --parameters @templates/start-stop-postgresql/link-postgresql-start-morning.json

az deployment group create \
  --resource-group "rg-tools-automation" \
  --template-file templates/job-schedule-template.bicep \
  --parameters @templates/start-stop-postgresql/link-postgresql-stop-evening.json
```

### Step 5: Configure Schedule Link Files

Before deploying schedule links, customize the JSON files with your environment values:

```bash
# Edit templates/start-stop-appservices/link-start-morning.json
{
  "parameters": {
    "automationAccountName": {
      "value": "auto-your-automation-account"  # Your automation account name
    },
    "runbookParameters": {
      "value": {
        "ResourceGroupName": "rg-your-appservices",     # Your App Services RG
        "AppServiceNames": "app1,app2,app3",            # Your App Service names
        "SubscriptionId": "your-subscription-id"        # Target subscription ID
      }
    }
  }
}

# Edit templates/start-stop-postgresql/link-postgresql-start-morning.json
{
  "parameters": {
    "automationAccountName": {
      "value": "auto-your-automation-account"  # Your automation account name
    },
    "runbookParameters": {
      "value": {
        "ResourceGroupName": "rg-your-postgresql",      # Your PostgreSQL RG
        "PostgreSQLNames": "your-postgresql-server",    # Your PostgreSQL server name
        "SubscriptionId": "your-subscription-id"        # Target subscription ID
      }
    }
  }
}
```

## 🔑 Key Information to Gather

Before starting the deployment, collect this information:

### Subscription Information

- **Tools Subscription ID**: Where automation account will be deployed
- **Target Subscription IDs**: Where your App Services/PostgreSQL servers are located
- **Subscription Names**: For authentication and role assignment scripts

### Resource Information

- **Automation Account Name**: e.g., `auto-your-organization-tools`
- **Resource Group Names**: Where your services are located
- **App Service Names**: Comma-separated list of App Services to manage
- **PostgreSQL Server Names**: Names of PostgreSQL Flexible Servers to manage

### Automation Account Identity

- **Principal ID**: Get this after automation account deployment:

```bash
 az automation account show --name "auto-your-automation-account" --resource-group "rg-tools-automation" --query "identity.principalId" --output tsv
```

## 🔐 Authentication Setup

The role assignment scripts require Microsoft Graph permissions. If you encounter authentication errors:

```bash
# Fix authentication issues
az logout
az login --scope https://graph.microsoft.com//.default
az account set --subscription "your-target-subscription"
# Re-run the role assignment script
```

```text
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
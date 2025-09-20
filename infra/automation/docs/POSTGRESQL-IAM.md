# PostgreSQL Server IAM Assignment Guide

This guide shows how to grant your **centralized automation account** (in Tools subscription) access to PostgreSQL Flexible Servers in **target subscriptions** using custom IAM roles and targeted assignments.

## �️ Architecture Overview

```
Tools Subscription               Target Subscription (Dev/Test/Prod)
┌─────────────────────┐         ┌─────────────────────────────────────┐
│  Automation Account │         │  Custom Role: PostgreSQL Operator  │
│  (Centralized)      │────────▶│  Assigned to: Specific PG Servers  │
│                     │         │                                     │
└─────────────────────┘         └─────────────────────────────────────┘
```

## 🎯 Approach

This **tag-based, cross-subscription** setup provides:

✅ **Centralized Management**: One automation account in Tools subscription manages all environments  
✅ **Tag-Based Targeting**: Use `automation_target: postgresql_server` tags for granular control  
✅ **Resource Group Scoped**: All servers in same RG, filtered by tags (same pattern as App Services)  
✅ **Minimal Permissions**: Custom roles with only start/stop permissions in each target subscription  
✅ **Security Isolation**: Each subscription has its own custom role definition  
✅ **Cross-Environment**: Works across Dev/Test/Prod subscriptions from single automation account  

## 🏷️ Required Server Tags

Tag your PostgreSQL servers with:
```
automation_target = postgresql_server
```

This follows the same pattern as your App Service automation - servers in the same resource group are filtered by this tag to determine which ones the automation account can manage.  

## 🚀 Two-Step Setup Process

> **Note**: This assumes you already have an automation account deployed from other templates (e.g., App Services automation). If not, deploy the automation account first using `main.bicep`.

### **Step 1: Create Custom Role (Target Subscription)**

Switch to each target subscription and create the PostgreSQL custom role:

```bash
# Switch to target subscription (Dev/Test/Prod)
az account set --subscription "target-subscription-name"

# Option A: Using parameter file (recommended)
az deployment sub create \
  --location "East US" \
  --template-file modules/postgresql-custom-role.bicep \
  --parameters @templates/postgresql-custom-role.bicepparam

# Option B: Inline parameters
az deployment sub create \
  --location "East US" \
  --template-file modules/postgresql-custom-role.bicep \
  --parameters customRoleName="PostgreSQL Flexible Server Operator"

# Check if role already exists first (optional)
az role definition list --name "PostgreSQL Flexible Server Operator" --query "[0].{Name:roleName, Id:id}" --output table
```

**📝 Note the Custom Role ID** from the deployment output.

### **Step 2: Assign Role to Tagged PostgreSQL Servers**

Assign the existing Tools automation account to tagged PostgreSQL servers in the target subscription:

```powershell
# Still in target subscription context
# Get your automation account principal ID (from your existing automation account)
$principalId = "automation-account-principal-id-from-tools-subscription"

# Get your custom role ID (from Step 1 output)  
$customRoleId = "/subscriptions/TARGET-SUB-ID/providers/Microsoft.Authorization/roleDefinitions/CUSTOM-ROLE-GUID"

# Assign to PostgreSQL servers tagged with automation_target = postgresql_server
.\scripts\Step2-Assign-PostgreSQL-Access.ps1 `
  -AutomationAccountPrincipalId $principalId `
  -CustomRoleId $customRoleId `
  -ResourceGroupName "rg-myproject-postgresql"

# Default tags: automation_target = postgresql_server
# To use different tags:
.\scripts\Step2-Assign-PostgreSQL-Access.ps1 `
  -AutomationAccountPrincipalId $principalId `
  -CustomRoleId $customRoleId `
  -ResourceGroupName "rg-myproject-postgresql" `
  -TagName "Environment" `
  -TagValue "Development"
```

## 🎯 **Complete Workflow Example**

Here's a complete example for adding PostgreSQL automation to your existing setup:

### **Scenario:**

- **Tools Subscription**: `tools-sub-12345` (contains existing automation account)
- **Target Subscription**: `dev-sub-67890` (contains PostgreSQL servers)
- **PostgreSQL Servers**: `psql-webapp-dev`, `psql-api-dev` in `rg-myproject-dev`
- **Server Tags**: Both servers tagged with `automation_target = postgresql_server`
- **Existing Principal ID**: `12345678-1234-1234-1234-123456789012` (from your automation account)

### **Step-by-Step Commands:**

```powershell
# === STEP 1: Create Custom Role (Target Subscription) ===
az account set --subscription "dev-sub-67890"

.\scripts\Step1-Create-PostgreSQL-Role.ps1 -WhatIf  # Preview first
.\scripts\Step1-Create-PostgreSQL-Role.ps1          # Create role

# Note the Role ID from output: "/subscriptions/dev-sub-67890/providers/Microsoft.Authorization/roleDefinitions/abcd1234-..."
```

```powershell
# === STEP 2: Assign to Tagged Servers (Target Subscription) ===
# Still in dev-sub-67890 context

$principalId = "12345678-1234-1234-1234-123456789012"  # From existing automation account
$roleId = "/subscriptions/dev-sub-67890/providers/Microsoft.Authorization/roleDefinitions/abcd1234-5678-90ab-cdef-123456789012"  # From Step 1

.\scripts\Step2-Assign-PostgreSQL-Access.ps1 `
  -AutomationAccountPrincipalId $principalId `
  -CustomRoleId $roleId `
  -ResourceGroupName "rg-myproject-dev" `
  -WhatIf  # Preview first

# Remove -WhatIf to execute
.\scripts\Step2-Assign-PostgreSQL-Access.ps1 `
  -AutomationAccountPrincipalId $principalId `
  -CustomRoleId $roleId `
  -ResourceGroupName "rg-myproject-dev"

# This will assign to servers tagged with: automation_target = postgresql_server
# === STEP 3: Assign to Specific Servers (Target Subscription) ===
# Still in dev-sub-67890 context

$principalId = "12345678-1234-1234-1234-123456789012"  # From Step 1
$roleId = "/subscriptions/dev-sub-67890/providers/Microsoft.Authorization/roleDefinitions/abcd1234-5678-90ab-cdef-123456789012"  # From Step 2

.\scripts\Step3-Assign-PostgreSQL-Access.ps1 `
  -AutomationAccountPrincipalId $principalId `
  -CustomRoleId $roleId `
  -PostgreSQLServerNames "psql-webapp-dev,psql-api-dev" `
  -ResourceGroupName "rg-myproject-dev" `
  -WhatIf  # Preview first

# Remove -WhatIf to execute
.\scripts\Step3-Assign-PostgreSQL-Access.ps1 `
  -AutomationAccountPrincipalId $principalId `
  -CustomRoleId $roleId `
  -ResourceGroupName "rg-myproject-dev"

# This will assign to servers tagged with: automation_target = postgresql_server
```

### **Verification:**

```bash
# Verify the automation account can access PostgreSQL servers
az role assignment list \
  --assignee "12345678-1234-1234-1234-123456789012" \
  --query "[?contains(roleDefinitionName, 'PostgreSQL')].{Server:resourceName, Role:roleDefinitionName}" \
  --output table
```

## 🔐 Required Permissions

The custom role **PostgreSQL Flexible Server Operator** includes:

| Permission | Purpose |
|------------|---------|
| `Microsoft.DBforPostgreSQL/flexibleServers/read` | Read PostgreSQL server properties |
| `Microsoft.DBforPostgreSQL/flexibleServers/*/read` | Read sub-resources |
| `Microsoft.DBforPostgreSQL/flexibleServers/start/action` | Start PostgreSQL servers |
| `Microsoft.DBforPostgreSQL/flexibleServers/stop/action` | Stop PostgreSQL servers |
| `Microsoft.Resources/subscriptions/resourceGroups/read` | Read resource group info |

## 🚀 Step-by-Step Process

### Option A: Automated Setup (Recommended for New Subscriptions)

Use the automated setup script that handles role creation and assignment:

```powershell
# Get your automation account principal ID from Azure Portal
$principalId = "your-automation-account-principal-id"

# Define your PostgreSQL resource groups
$resourceGroups = @("rg-myproject-postgresql", "rg-another-postgresql")

# Run the automated setup
.\scripts\Setup-PostgreSQLAutomation.ps1 `
  -AutomationAccountPrincipalId $principalId `
  -PostgreSQLResourceGroups $resourceGroups `
  -SubscriptionId "your-subscription-id"
```

This script will:
- ✅ Check if the custom role already exists
- ✅ Create the custom role if needed
- ✅ Assign permissions to all specified resource groups
- ✅ Verify the final configuration

### Option B: Manual Step-by-Step (For Existing Roles)

If you prefer manual control or the role already exists:

### 1. Create Custom Role (One-time setup per subscription)

Create the PostgreSQL Flexible Server Operator custom role at subscription level:

```bash
# Deploy custom role to subscription (one-time setup)
az deployment sub create \
  --location "East US" \
  --template-file modules/postgresql-custom-role.bicep \
  --parameters customRoleName="PostgreSQL Flexible Server Operator"
```

**Note**: Save the role definition ID from the output - you'll need it for step 4.

### 2. Get Automation Account Principal ID

Get the managed identity Principal ID from Azure Portal:
1. Go to **Azure Portal** → **Automation Account** (`auto-myproject-tools`)
2. Go to **Identity** → **System assigned**
3. Copy the **Object (principal) ID**

### 3. Login and Set Subscription Context

Ensure you're authenticated and in the correct subscription:

```bash
# Login to Azure CLI
az login

# List available subscriptions
az account list --output table

# Set the subscription where your PostgreSQL servers are located
az account set --subscription "your-postgresql-subscription-id-or-name"

# Verify correct subscription is selected
az account show --query name --output tsv
```

### 4. Assign Permissions Using Bicep Templates

#### Option A: Via Main Template (Recommended)

Update your main automation deployment to include PostgreSQL resource groups:

```bash
# Deploy automation with PostgreSQL IAM
az deployment group create \
  --resource-group "rg-automation-tools" \
  --template-file main.bicep \
  --parameters @main.bicepparam \
    postgreSQLResourceGroups='["rg-myproject-postgresql","rg-another-postgresql"]' \
    postgreSQLCustomRoleId="/subscriptions/YOUR-SUB-ID/providers/Microsoft.Authorization/roleDefinitions/YOUR-CUSTOM-ROLE-GUID"
```

#### Option B: Using PowerShell Script

Use the provided script for individual server assignments:

```powershell
# Get your automation account principal ID (from step 2)
$principalId = "your-automation-account-principal-id"

# Get your custom role ID (from step 1 output)
$customRoleId = "/subscriptions/YOUR-SUB-ID/providers/Microsoft.Authorization/roleDefinitions/YOUR-CUSTOM-ROLE-GUID"

# Assign permissions to all PostgreSQL servers in a resource group
.\scripts\Assign-PostgreSQLRoles-Clean.ps1 -PrincipalId $principalId -ResourceGroupName "rg-myproject-postgresql" -CustomRoleId $customRoleId

# Or with tag filtering
.\scripts\Assign-PostgreSQLRoles-Clean.ps1 -PrincipalId $principalId -ResourceGroupName "rg-myproject-postgresql" -TagName "Environment" -TagValue "Development" -CustomRoleId $customRoleId
```

### 5. Verify Permissions

Check the role assignments:

```bash
# Verify PostgreSQL role assignments
az role assignment list --assignee YOUR-PRINCIPAL-ID --query "[?contains(roleDefinitionName, 'PostgreSQL')].{Role:roleDefinitionName, Scope:scope}" --output table
```

## 📝 Example Parameter Files

### main.bicepparam with PostgreSQL

```bicep
using './main.bicep'

param automationAccountName = 'auto-myproject-tools'
param appServiceResourceGroups = ['rg-myproject-apps']
param postgreSQLResourceGroups = ['rg-myproject-postgresql', 'rg-another-postgresql']
param postgreSQLCustomRoleId = '/subscriptions/12345678-1234-1234-1234-123456789012/providers/Microsoft.Authorization/roleDefinitions/abcd1234-5678-90ab-cdef-123456789012'
param customTags = {
  project: 'myproject'
  environment: 'tools'
}
```

## 🛠️ Testing Access

After assignment, test the automation account can access PostgreSQL servers:

```powershell
# Test reading PostgreSQL server (should work)
Get-AzPostgreSqlFlexibleServer -ResourceGroupName "rg-myproject-postgresql" -Name "psql-myserver-dev"

# Test starting PostgreSQL server (should work)
Start-AzPostgreSqlFlexibleServer -ResourceGroupName "rg-myproject-postgresql" -Name "psql-myserver-dev"

# Test deleting PostgreSQL server (should fail - good!)
Remove-AzPostgreSqlFlexibleServer -ResourceGroupName "rg-myproject-postgresql" -Name "psql-myserver-dev"
```

## 🔍 Troubleshooting

### Common Issues

1. **"Insufficient privileges" error**
   - Verify the custom role was created successfully
   - Check the role assignment exists: `az role assignment list --assignee YOUR-PRINCIPAL-ID`

2. **"Resource not found" error**
   - Verify you're in the correct subscription
   - Check the PostgreSQL server name and resource group

3. **"Authentication failed" error**
   - Ensure the automation account managed identity is enabled
   - Verify you're using the correct principal ID

### Required Azure Modules

Ensure these PowerShell modules are installed in your automation account:

```powershell
# Required modules for PostgreSQL automation
Install-Module -Name Az.Accounts -Force
Install-Module -Name Az.PostgreSql -Force
```

## 🔐 Security Notes

- The custom role provides minimal permissions (start/stop only)
- Consider creating separate roles for different environments
- Regularly audit role assignments
- Use tag-based filtering to limit which servers can be managed
- Monitor automation runbook execution logs for unauthorized access attempts

## 📚 Related Documentation

- [PowerShell Runbook Templates](../templates/start-stop-postgresql/)
- [Scheduling Guide](SCHEDULING.md)
- [Main Automation Setup](../README.md)

## 🏃 Quick Reference

### One-Command Setup
```powershell
.\scripts\Setup-PostgreSQLAutomation.ps1 -AutomationAccountPrincipalId "YOUR-PRINCIPAL-ID" -PostgreSQLResourceGroups @("rg-postgresql-dev","rg-postgresql-prod")
```

### Check Existing Role
```bash
az role definition list --name "PostgreSQL Flexible Server Operator"
```

### Verify Permissions
```bash
az role assignment list --assignee YOUR-PRINCIPAL-ID --query "[?contains(roleDefinitionName, 'PostgreSQL')]"
```
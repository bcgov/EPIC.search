# App Service IAM Assignment Guide

This guide shows how to grant your automation account access to specific App Services using the IAM Bicep template.

## 🎯 Approach

Instead of granting resource group-level permissions, we assign **Website Contributor** role directly to individual App Services. This provides:

✅ **Least Privilege**: Only access to specific App Services
✅ **Cross-Subscription**: Works across Dev/Test/Prod subscriptions  
✅ **Granular Control**: Pick exactly which apps the automation can manage
✅ **Audit Trail**: Clear visibility of what has access
✅ **Multiple App Services**: Assign permissions to multiple apps in one deployment

## 🚀 Step-by-Step Process

### 1. Get Automation Account Principal ID

Get the managed identity Principal ID from Azure Portal:
1. Go to **Azure Portal** → **Automation Account** (`auto-myproject-tools`)
2. Go to **Identity** → **System assigned**
3. Copy the **Object (principal) ID**

### 2. Login and Set Subscription Context

Ensure you're authenticated and in the correct subscription:

```powershell
# Login to Azure CLI
az login

# List available subscriptions
az account list --output table

# Set the subscription where your App Services are located
az account set --subscription "your-app-services-subscription-id-or-name"

# Verify correct subscription is selected
az account show --query name --output tsv
```

### 3. Assign Permissions to App Services

Use the IAM Bicep template to assign Website Contributor role:

```powershell
# Single App Service
az deployment group create `
  --resource-group "rg-test-apps" `
  --template-file app-service-iam.bicep `
  --parameters automationAccountPrincipalId="YOUR_PRINCIPAL_ID" `
  --parameters appServiceNames="app-myproject-frontend-test"

# Multiple App Services (comma-separated)
az deployment group create `
  --resource-group "rg-test-apps" `
  --template-file app-service-iam.bicep `
  --parameters automationAccountPrincipalId="YOUR_PRINCIPAL_ID" `
  --parameters appServiceNames="app-myproject-frontend-test,app-myproject-backend-test,app-myproject-api-test"
```

### 3. Cross-Subscription Assignments

For App Services in different subscriptions, set the subscription context first:

```powershell
# Switch to Test subscription and assign permissions
az account set --subscription "your-test-subscription-id"
az deployment group create `
  --resource-group "rg-test-apps" `
  --template-file app-service-iam.bicep `
  --parameters automationAccountPrincipalId="YOUR_PRINCIPAL_ID" `
  --parameters appServiceNames="test-app1,test-app2"

# Switch to Prod subscription and assign permissions  
az account set --subscription "your-prod-subscription-id"
az deployment group create `
  --resource-group "rg-prod-apps" `
  --template-file app-service-iam.bicep `
  --parameters automationAccountPrincipalId="YOUR_PRINCIPAL_ID" `
  --parameters appServiceNames="prod-app1,prod-app2"
```

### 4. Test Access

Test that the automation account can start/stop your App Services:

```powershell
# Test starting App Services
Start-AzAutomationRunbook `
  -AutomationAccountName "auto-myproject-tools" `
  -ResourceGroupName "rg-tools-automation" `
  -Name "Start-AppServices" `
  -Parameters @{
    ResourceGroupName = "rg-test-apps"
    AppServiceNames = "app-myproject-frontend-test,app-myproject-backend-test"
    SubscriptionId = "your-test-subscription-id"
    WaitForStartup = $true
  }
```

## 📋 Verification

Check permissions were assigned correctly:

```powershell
# List role assignments for specific App Service
az role assignment list `
  --scope "/subscriptions/test-sub-id/resourceGroups/rg-test-apps/providers/Microsoft.Web/sites/app-myproject-frontend-test" `
  --output table
```

## � Troubleshooting Authentication Issues

### Common Issue: Microsoft Graph Authentication Required

When assigning IAM roles, you may encounter this error:

```text
(pii). Status: Response_Status.Status_InteractionRequired, Error code: 3399614467
Please explicitly log in with:
az login --scope https://graph.microsoft.com/.default
```

**Root Cause**: Azure CLI needs Microsoft Graph permissions for role assignments, and switching subscriptions doesn't refresh these tokens.

**Solution**: Explicitly log out and back in with the correct scope:

```powershell
# Step 1: Log out completely
az logout

# Step 2: Log back in with Microsoft Graph scope
az login --scope https://graph.microsoft.com//.default

# Step 3: Set your subscription context
az account set --subscription "your-target-subscription"

# Step 4: Verify you're in the correct subscription
az account show --query name --output tsv

# Step 5: Retry your role assignment
```

**Important**: Simply running `az account set` to switch subscriptions does **NOT** refresh the Microsoft Graph authentication tokens. You must explicitly log out and log back in.

## �🔄 Managing Permissions

### Add New App Service

Deploy the IAM template again with updated App Service list:

```powershell
az deployment group create `
  --resource-group "rg-test-apps" `
  --template-file app-service-iam.bicep `
  --parameters automationAccountPrincipalId="YOUR_PRINCIPAL_ID" `
  --parameters appServiceNames="existing-app1,existing-app2,new-app3"
```

### Remove Access

```powershell
az role assignment delete `
  --assignee YOUR_PRINCIPAL_ID `
  --role "Website Contributor" `
  --scope "/subscriptions/sub-id/resourceGroups/rg-name/providers/Microsoft.Web/sites/app-name"
```

This approach gives you precise control over which App Services your automation account can manage! 🎯
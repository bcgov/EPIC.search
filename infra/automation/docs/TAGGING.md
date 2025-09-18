# Simplified Tagging Strategy

This document describes the simplified tagging approach used across all infrastructure components to ensure compliance with organizational policies.

## 🏷️ **Required Organizational Tags Only**

All Azure resources include only the essential tags required for organizational and billing compliance:

```bicep
var organizationalTags = {
  account_coding: 'your-account-coding'
  billing_group: 'your-billing-group'
  ministry_name: 'your-ministry'
}
```

No additional operational tags are applied automatically. Custom tags can be added as needed per deployment.

## 🎯 **Implementation Pattern**

Each Bicep template uses this standardized approach:

```bicep
@description('Additional custom tags to merge with required organizational tags')
param customTags object = {}

// Required organizational tags
var organizationalTags = {
  account_coding: 'your-account-coding'
  billing_group: 'your-billing-group'
  ministry_name: 'your-ministry'
}

// Combine organizational tags with any custom tags
var allTags = union(organizationalTags, customTags)

// Apply to resource
resource myResource 'Microsoft.SomeService/someType@2024-01-01' = {
  name: 'resource-name'
  location: location
  tags: allTags
  // ... other properties
}
```

### **Parameter File Examples**

```bicep-params
using './main.bicep'

param automationAccountName = 'auto-myproject-dev'
param location = 'East US'

// Optional custom tags only
// param customTags = {
//   Owner: 'platform-team'
//   CostCenter: 'development'
//   Environment: 'dev'
// }
```

## ✅ **Validation Commands**

### **Check Resource Tags**

```bash
# Verify automation account tags (should show only organizational + custom tags)
az automation account show \
  --automation-account-name "auto-myproject-dev" \
  --resource-group "rg-automation-dev" \
  --query "tags"

# Expected output (minimal):
# {
#   "account_coding": "your-account-coding",
#   "billing_group": "your-billing-group", 
#   "ministry_name": "your-ministry"
# }
```

## 🚨 **Key Changes**

1. **Removed Operational Tags**: No automatic Environment, Project, Application, or ManagedBy tags
2. **Simplified Parameters**: No environment/project parameters required
3. **Custom Tags Only**: Add any additional tags via customTags parameter as needed
4. **Policy Compliance**: Still meets organizational requirements with minimal tagging
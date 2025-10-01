# Automation Deployment

## Quick Start

### 1. Copy and customize parameters

```powershell
# Copy the example file
Copy-Item "deploy-subscription.example.json" "deploy-subscription.dev.json"

# Edit deploy-subscription.dev.json with your values:
# - resourceGroupName: Resource group for automation resources (creates if not exists)
# - location: Azure region for deployment
# - automationAccountName: Name for your automation account
# - sku: "Basic" or "Free"
# - customTags: Optional additional tags for your resources
```

### 2. Deploy Automation Account

```powershell
az deployment sub create \
  --location "Canada Central" \
  --template-file "deploy-subscription.bicep" \
  --parameters "@deploy-subscription.dev.json"
```

**Note:** The template automatically creates the resource group if it doesn't exist, or deploys into it if it does exist (idempotent).

## Alternative: Using Bicep Parameters

You can also use the native Bicep parameters file:

```powershell
# Edit deploy-subscription.bicepparam with your values
# Then deploy:
az deployment sub create \
  --location "Canada Central" \
  --template-file "deploy-subscription.bicep" \
  --parameters "deploy-subscription.bicepparam"
```

## Files

- `deploy-subscription.bicep` - Main deployment template (creates RG and automation account)
- `deploy-subscription.example.json` - Parameter template with placeholders (commit to git)
- `deploy-subscription.dev.json` - Your environment values (excluded from git)
- `deploy-subscription.bicepparam` - Alternative Bicep-native parameters format

## Environment Files

Create separate parameter files for each environment:

- `deploy-subscription.dev.json`
- `deploy-subscription.test.json`
- `deploy-subscription.prod.json`
- `deploy-subscription.tools.json`

These files are excluded from git via `.gitignore`.

## Next Steps

After deploying the automation account:

1. **Configure Runbooks** - Deploy runbooks for specific automation tasks
2. **Set Up Schedules** - Configure timing for automated operations
3. **Assign Permissions** - Set up cross-subscription IAM for managed identity

See the main [README.md](README.md) for detailed information about:

- Runbook templates
- IAM configuration
- Scheduling automation
- Cross-subscription setup

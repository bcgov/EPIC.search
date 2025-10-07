# Azure Container Registry (ACR) Deployment

## Quick Start

### 1. Copy and customize parameters

```powershell
Copy-Item "deploy-registry.example.json" "deploy-registry.dev.json"
# Edit deploy-registry.dev.json with your values
```

### 2. Deploy ACR

```powershell
az deployment sub create \
  --location "Canada Central" \
  --template-file "deploy-registry.bicep" \
  --parameters "@deploy-registry.dev.json"
```

## Files

- `deploy-registry.bicep` - Subscription wrapper that creates RG and deploys ACR
- `registry.bicep` - Resource group-scoped ACR module
- `deploy-registry.example.json` - Parameter template (commit to git)
- `deploy-registry.dev.json` - Environment parameters (gitignored)

## Notes

- Admin user is disabled by default. Prefer AAD tokens or workload identity federation.
- For private network access, add a private endpoint and set `publicNetworkAccess` to `Disabled`.
- For content trust or retention policies, extend the `properties.policies` block in `registry.bicep`.
- Optional: You can create common scope maps (pull/push) via the `scopeMaps` parameter in the example file.
- Webhooks: We can add webhook creation later using secure parameters for service URIs once your target service endpoints are finalized.

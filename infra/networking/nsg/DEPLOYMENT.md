# NSG Deployment

## Quick Start

### 1. Copy and customize parameters
```powershell
# Copy the example file
Copy-Item "deploy-all-nsgs.example.json" "deploy-all-nsgs.dev.json"

# Edit deploy-all-nsgs.dev.json with your values:
# - environmentSuffix: "dev" (or "test", "prod")
# - location: Your Azure region
```

### 2. Deploy NSGs
```powershell
az deployment sub create \
  --location "Canada Central" \
  --template-file "deploy-all-nsgs.bicep" \
  --parameters "@deploy-all-nsgs.dev.json"
```

## Files
- `deploy-all-nsgs.bicep` - Main NSG template
- `deploy-all-nsgs.example.json` - Parameter template (commit to git)
- `deploy-all-nsgs.dev.json` - Your environment values (excluded from git)

## Environment Files
Create separate parameter files for each environment:
- `deploy-all-nsgs.dev.json`
- `deploy-all-nsgs.test.json` 
- `deploy-all-nsgs.prod.json`

These files are excluded from git via `.gitignore`.
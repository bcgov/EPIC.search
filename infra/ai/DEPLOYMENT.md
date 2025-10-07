# AI Services Deployment (OpenAI, Computer Vision, Document Intelligence) with Private Endpoints

## Overview

- This folder contains subscription-scope wrappers to deploy Azure OpenAI, Computer Vision, and Document Intelligence accounts, each with a Private Endpoint into your shared VNet.
- Private endpoints are created in the existing `snet-private-endpoints-{env}` subnet of your VNet. Private DNS is assumed to be handled by policy (no zones/links are created here).
- Parameter files follow the pattern: copy `*.example.json` to `*.dev.json`, then edit locally. The `*.dev.json` files are gitignored by default.
- You can deploy services individually or use the consolidated `deploy-ai-all.bicep` to deploy all three together with shared inputs.

## Prerequisites

- Azure CLI authenticated to the correct subscription.
- An existing VNet and subnet for private endpoints:
  - VNet subscription ID, resource group name, and VNet name.
  - Subnet named `snet-private-endpoints-{environmentSuffix}` must already exist.
- Sufficient permissions to create Resource Groups, Cognitive Services accounts, and Private Endpoints (including cross-subscription if your VNet is in another subscription).
- Region/model availability: Azure OpenAI is region-limited; ensure selected models/sku/capacity are supported in your chosen regions.

## Quick Start

1. Copy and customize parameters

```powershell
Copy-Item "deploy-ai-openai.example.json" "deploy-ai-openai.dev.json"
# Edit deploy-ai-openai.dev.json with your VNet/subnet info and names
```

1. Deploy (subscription scope)

```powershell
az deployment sub create `
  --location "Canada East" `
  --template-file "infra/ai/deploy-ai-openai.bicep" `
  --parameters "@infra/ai/deploy-ai-openai.dev.json"
```

Notes

- Private endpoints are placed into the existing `snet-private-endpoints-{env}` subnet of your VNet.
- Private DNS is assumed to be handled by policy; this template does not create zones or links.
- Update model deployments in the params to add additional models or capacities.
- Ensure the region supports Azure OpenAI and the model/sku/capacity you request.
- `*.dev.json` parameter files are ignored by git; keep secrets/config local.

## Computer Vision

1. Copy and customize parameters

```powershell
Copy-Item "deploy-ai-vision.example.json" "deploy-ai-vision.dev.json"
# Edit deploy-ai-vision.dev.json with your VNet/subnet info and names
```

1. Deploy (subscription scope)

```powershell
az deployment sub create `
  --location "Canada Central" `
  --template-file "infra/ai/deploy-ai-vision.bicep" `
  --parameters "@infra/ai/deploy-ai-vision.dev.json"
```

## Document Intelligence

1. Copy and customize parameters

```powershell
Copy-Item "deploy-ai-document-intelligence.example.json" "deploy-ai-document-intelligence.dev.json"
# Edit deploy-ai-document-intelligence.dev.json with your VNet/subnet info and names
```

1. Deploy (subscription scope)

```powershell
az deployment sub create `
  --location "Canada Central" `
  --template-file "infra/ai/deploy-ai-document-intelligence.bicep" `
  --parameters "@infra/ai/deploy-ai-document-intelligence.dev.json"
```

## Deploy all three services together

1. Copy and customize parameters

```powershell
Copy-Item "deploy-ai-all.example.json" "deploy-ai-all.dev.json"
# Edit deploy-ai-all.dev.json with your names, locations, VNet details, and OpenAI deployments (optional)
```

1. Deploy (subscription scope)

```powershell
az deployment sub create `
  --location "Canada Central" `
  --template-file "infra/ai/deploy-ai-all.bicep" `
  --parameters "@infra/ai/deploy-ai-all.dev.json"
```

## Verify and outputs

- The deployment will return outputs including each account's ID and endpoint, plus each private endpoint ID.
- You can also review the deployment in the Azure Portal (Subscription > Deployments) to view outputs and logs.

## Troubleshooting

- Model/region not supported: verify your chosen region supports Azure OpenAI and the specific models/sku/capacity in your `openaiDeployments`.
- Subnet not found: ensure the VNet and `snet-private-endpoints-{environmentSuffix}` subnet exist and the names/subscription/RG match your params.
- Cross-subscription VNet: you need permission on the VNet subscription/RG to create private endpoints.
- Private Endpoint approval pending: some environments require manual approval on the target account; approve the connection if it remains in Pending.
- DNS resolution failures: this template assumes policy-managed Private DNS. If you don't have such a policy, create the zones/links for Cognitive Services private endpoints.
- Custom subdomain in use: account names become the custom subdomain; ensure the name is globally unique per service.

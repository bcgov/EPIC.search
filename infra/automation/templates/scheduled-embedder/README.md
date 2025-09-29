# ScheduledEmbedder Automation

This directory contains automation components for managing ScheduledEmbedder processes that require both Virtual Machine and PostgreSQL server coordination.

## Files Overview

- **`deploy-scheduled-embedder-runbook.bicep`** - Bicep template to deploy the ScheduledEmbedder runbook to Azure Automation Account
- **`ScheduledEmbedder.ps1`** - PowerShell runbook that orchestrates VM startup, PostgreSQL startup, embedding process, and cleanup
- **`publish-runbooks.ps1`** - Script to publish the runbook to the Automation Account
- **`Assign-ScheduledEmbedderRoles.ps1`** - Script to assign necessary IAM roles (Virtual Machine Contributor + PostgreSQL Flexible Server Operator)
- **`link-embedder-mon-thurs.json`** - Schedule link parameters for Embedder-Mon-Thurs schedule (8:00 PM PST, Monday-Thursday)

## Required Permissions

The managed identity running these runbooks needs:

- **Virtual Machine Contributor** role on target VMs
- **PostgreSQL Flexible Server Operator** role on target PostgreSQL servers (custom role from PostgreSQL automation)

## Usage Pattern

1. Deploy the runbook: `az deployment group create --template-file deploy-scheduled-embedder-runbook.bicep`
2. Assign IAM roles: `.\Assign-ScheduledEmbedderRoles.ps1 -PrincipalId <managed-identity-id>`
3. Deploy the Embedder-Mon-Thurs schedule: `az deployment group create --template-file ../templates/schedule-template.bicep --parameters @../embedder-mon-thurs-schedule.json`
4. Link runbook to schedule: `az deployment group create --template-file ../templates/job-schedule-template.bicep --parameters @link-embedder-mon-thurs.json`

## Runbook Logic

The ScheduledEmbedder runbook follows this sequence:

1. Check and start PostgreSQL Flexible Server if stopped
2. Check and start Virtual Machine if deallocated  
3. Wait for PostgreSQL to accept connections
4. Run the embedder Python script with optional parameters
5. Optionally stop PostgreSQL Flexible Server (controlled by ShutdownPostgres parameter)
6. Deallocate Virtual Machine if it was started by the script
7. Error handling includes proper resource cleanup

## Parameters

### Required Parameters (must be provided via schedule link)

- **SubscriptionId** - Azure subscription ID containing the resources
- **ResourceGroupName** - Resource group containing both VM and PostgreSQL server
- **VMName** - Name of the Virtual Machine to start/stop
- **ScriptDir** - Full path to the embedder script directory on the VM
- **PostgreSQLName** - Name of the PostgreSQL Flexible Server
- **PostgresHost** - Fully qualified domain name of the PostgreSQL server

### Optional Parameters (have sensible defaults)

- **ProjectId** - Default: "" (empty, optional filter for embedding)
- **TimedMinutes** - Default: 60 (runtime limit for embedder script)
- **PostgresPort** - Default: 5432
- **ShutdownPostgres** - Default: true (automatically stop PostgreSQL after processing)

## Customization

The runbook is designed for the EPIC.search embedder workflow and provides:

- Intelligent resource lifecycle management (only starts/stops resources as needed)
- PostgreSQL connection readiness checking
- Configurable embedding script parameters
- Timestamped logging
- Proper resource cleanup and error handling
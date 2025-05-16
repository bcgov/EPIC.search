{
  billingGroup: 'epic-search'
  tags: {
    application: 'EPIC.search'
    component: 'database'
  }
  serverName: 'vm-postgresql-vector-test'
  skuName: 'Standard_D4s_v3'
  storageSizeGB: 1024
  version: '16'
  adminUser: 'pgadmin'
  // Note: adminPassword should be provided at deployment time or retrieved from KeyVault
  adminObjectId: '9851ae78-4034-45d5-9199-9a68a22c634d'
  privateDnsZoneId: '' // No private DNS zone
}

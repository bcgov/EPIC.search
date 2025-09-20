// Centralized tagging configuration for all infrastructure
// This file provides consistent tags across all infrastructure components

@description('Account coding for billing and tracking')
param accountCoding string

@description('Billing group for cost allocation')
param billingGroup string

@description('Ministry or department name')
param ministryName string

@description('Additional custom tags to merge with standard tags')
param customTags object = {}

// Standard organizational tags required by policy
var organizationalTags = {
  account_coding: accountCoding
  billing_group: billingGroup
  ministry_name: ministryName
}

// Combine all tags
var allTags = union(organizationalTags, customTags)

// Function to generate tags for resources
@export()
func generateTags(accountCoding string, billingGroup string, ministryName string, customTags object) object => union(
  {
    account_coding: accountCoding
    billing_group: billingGroup
    ministry_name: ministryName
  },
  customTags
)

// Outputs
output tags object = allTags
output organizationalTags object = organizationalTags

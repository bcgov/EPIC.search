#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get __dirname equivalent in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Function to load .env file
function loadEnvFile(envPath) {
  if (!fs.existsSync(envPath)) {
    console.warn(`Environment file ${envPath} not found`);
    return {};
  }
  
  const envContent = fs.readFileSync(envPath, 'utf8');
  const envVars = {};
  
  envContent.split('\n').forEach(line => {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith('#')) {
      const [key, ...valueParts] = trimmed.split('=');
      if (key && valueParts.length > 0) {
        envVars[key.trim()] = valueParts.join('=').trim();
      }
    }
  });
  
  return envVars;
}

// Get target environment from command line argument or default to 'local'
const targetEnv = process.argv[2] || 'local';
console.log(`Generating config for environment: ${targetEnv}`);

// Load environment-specific file
const envFilePath = path.join(__dirname, `../.env.${targetEnv}`);
const envVars = loadEnvFile(envFilePath);

// Merge with process.env (process.env takes precedence)
const config = {
  VITE_API_URL: process.env.VITE_API_URL || envVars.VITE_API_URL || '/api',
  VITE_APP_TITLE: process.env.VITE_APP_TITLE || envVars.VITE_APP_TITLE || 'EPIC.Search',
  VITE_APP_URL: process.env.VITE_APP_URL || envVars.VITE_APP_URL || 'http://localhost:3000',
  VITE_OIDC_AUTHORITY: process.env.VITE_OIDC_AUTHORITY || envVars.VITE_OIDC_AUTHORITY || 'https://dev.loginproxy.gov.bc.ca/auth/realms/eao-epic',
  VITE_CLIENT_ID: process.env.VITE_CLIENT_ID || envVars.VITE_CLIENT_ID || 'epic-search',
};

// Handle PROXY_API_URL for the API URL
const apiUrl = process.env.PROXY_API_URL || envVars.PROXY_API_URL || config.VITE_API_URL;

// Create config.js content
const configContent = `window._env_ = {
  VITE_API_URL: "${apiUrl.endsWith('/api') ? apiUrl : apiUrl + '/api'}",
  VITE_APP_TITLE: "${config.VITE_APP_TITLE}",
  VITE_APP_URL: "${config.VITE_APP_URL}",
  VITE_OIDC_AUTHORITY: "${config.VITE_OIDC_AUTHORITY}",
  VITE_CLIENT_ID: "${config.VITE_CLIENT_ID}",
};
`;

// Write to public/config.js
const publicDir = path.join(__dirname, '../public');
if (!fs.existsSync(publicDir)) {
  fs.mkdirSync(publicDir, { recursive: true });
}

fs.writeFileSync(path.join(publicDir, 'config.js'), configContent);
console.log(`Generated config.js for ${targetEnv} environment`);
console.log(`API URL: ${apiUrl}`);
console.log(`OIDC Authority: ${config.VITE_OIDC_AUTHORITY}`);

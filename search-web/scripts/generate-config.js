#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get __dirname equivalent in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Function to load .env file
function loadEnvFile() {
  const envPath = path.join(__dirname, '../.env');
  if (fs.existsSync(envPath)) {
    let envContent;
    try {
      // Try reading as UTF-8 first
      envContent = fs.readFileSync(envPath, 'utf8');
    } catch (error) {
      // If that fails, try UTF-16
      envContent = fs.readFileSync(envPath, 'utf16le');
    }
    
    // Clean up any BOM or null characters
    envContent = envContent.replace(/\uFEFF/g, '').replace(/\0/g, '');
    
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
  return {};
}

// Load environment variables from .env file
const envVars = loadEnvFile();

// Helper function to get env variable with fallback
const getEnv = (key, defaultValue = '') => {
  return process.env[key] || envVars[key] || defaultValue;
};

// Get the target API URL from environment or default
const apiUrl = getEnv('PROXY_API_URL', 'http://127.0.0.1:8081/api');

// Create config.js content
const configContent = `window._env_ = {
  VITE_API_URL: "${apiUrl.endsWith('/api') ? apiUrl : apiUrl + '/api'}",
  VITE_KEYCLOAK_URL: "${getEnv('VITE_KEYCLOAK_URL', 'https://dev.loginproxy.gov.bc.ca')}",
  VITE_KEYCLOAK_CLIENT: "${getEnv('VITE_KEYCLOAK_CLIENT', 'epicscaffold-web')}",
  VITE_KEYCLOAK_REALM: "${getEnv('VITE_KEYCLOAK_REALM', 'eao-epic')}",
  VITE_ENV: "${getEnv('VITE_ENV', 'local')}",
  VITE_APP_TITLE: "${getEnv('VITE_APP_TITLE', 'EPIC.Search')}",
  VITE_APP_URL: "${getEnv('VITE_APP_URL', 'http://localhost:5173')}",
  VITE_OIDC_AUTHORITY: "${getEnv('VITE_OIDC_AUTHORITY', 'https://dev.loginproxy.gov.bc.ca/auth/realms/eao-epic')}",
  VITE_CLIENT_ID: "${getEnv('VITE_CLIENT_ID', 'epic-submit')}",
  VITE_SYSTEM_NOTE: "${getEnv('VITE_SYSTEM_NOTE', '')}",
};
`;

// Write to public/config.js
const publicDir = path.join(__dirname, '../public');
if (!fs.existsSync(publicDir)) {
  fs.mkdirSync(publicDir, { recursive: true });
}

fs.writeFileSync(path.join(publicDir, 'config.js'), configContent);
console.log('Generated config.js with API URL:', apiUrl);

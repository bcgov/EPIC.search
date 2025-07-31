#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get __dirname equivalent in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Get the target API URL from environment or default
const apiUrl = process.env.PROXY_API_URL || 'http://127.0.0.1:8081/api';

// Create config.js content
const configContent = `window._env_ = {
  VITE_API_URL: "${apiUrl.endsWith('/api') ? apiUrl : apiUrl + '/api'}",
  VITE_KEYCLOAK_URL: "${process.env.VITE_KEYCLOAK_URL || 'https://dev.loginproxy.gov.bc.ca'}",
  VITE_KEYCLOAK_CLIENT: "${process.env.VITE_KEYCLOAK_CLIENT || 'epicscaffold-web'}",
  VITE_KEYCLOAK_REALM: "${process.env.VITE_KEYCLOAK_REALM || 'eao-epic'}",
  VITE_ENV: "${process.env.VITE_ENV || 'local'}",
  VITE_APP_TITLE: "${process.env.VITE_APP_TITLE || 'EPIC.Search'}",
  VITE_APP_URL: "${process.env.VITE_APP_URL || 'http://localhost:5173'}",
  VITE_OIDC_AUTHORITY: "${process.env.VITE_OIDC_AUTHORITY || 'https://dev.loginproxy.gov.bc.ca/auth/realms/eao-epic'}",
  VITE_CLIENT_ID: "${process.env.VITE_CLIENT_ID || 'epic-submit'}",
};
`;

// Write to public/config.js
const publicDir = path.join(__dirname, '../public');
if (!fs.existsSync(publicDir)) {
  fs.mkdirSync(publicDir, { recursive: true });
}

fs.writeFileSync(path.join(publicDir, 'config.js'), configContent);
console.log('Generated config.js with API URL:', apiUrl);

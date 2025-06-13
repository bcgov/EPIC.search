# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react/# EPIC.Search

A React-based web application for searching and viewing environmental assessment documents.

## Prerequisites

- Node.js (v14 or higher)
- npm (v6 or higher)
- A running instance of the EPIC Search API

## Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd search-web
```

2. Install dependencies:

```bash
npm install
```

3. Create environment configuration:

   - Copy `sample.env` to `.env`
   - Update the environment variables as needed:

```properties
VITE_API_URL=http://localhost:3200/api
VITE_KEYCLOAK_URL=https:/dev.loginproxy.gov.bc.ca
VITE_KEYCLOAK_CLIENT=epicscaffold-web
VITE_KEYCLOAK_REALM=eao-epic
VITE_ENV=local
VITE_APP_TITLE=EPIC.Search
VITE_APP_URL=http://localhost:5173
VITE_OIDC_AUTHORITY=https://dev.loginproxy.gov.bc.ca/auth/realms/eao-epic
VITE_CLIENT_ID=epic-submit
```

## Development

Start the development server:

```bash
npm run dev
```

The application will be available at http://localhost:5173

## Building for Production

```bash
npm run build
```

The production build will be available in the `dist` directory.

## Docker Support

Build the Docker image:

```bash
docker build -t epic-search-web .
```

Run the container:

```bash
docker run -p 8080:80 epic-search-web
```) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type aware lint rules:

- Configure the top-level `parserOptions` property like this:

```js
export default {
  // other rules...
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    project: ['./tsconfig.json', './tsconfig.node.json'],
    tsconfigRootDir: __dirname,
  },
}
```

- Replace `plugin:@typescript-eslint/recommended` to `plugin:@typescript-eslint/recommended-type-checked` or `plugin:@typescript-eslint/strict-type-checked`
- Optionally add `plugin:@typescript-eslint/stylistic-type-checked`
- Install [eslint-plugin-react](https://github.com/jsx-eslint/eslint-plugin-react) and add `plugin:react/recommended` & `plugin:react/jsx-runtime` to the `extends` list

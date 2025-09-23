# EPIC.Search Technical Documentation

## Architecture Overview

This application is built using:

- React + TypeScript
- Vite as the build tool
- Material-UI for components
- TanStack Router for routing
- **OIDC/Keycloak for authentication** (required for search and stats)
- Axios for API communication

## Authentication Architecture

The application implements a **protected route pattern**:

- **Public Routes**: Home page (`/`) - accessible without authentication
- **Protected Routes**: Search (`/search`) and Statistics (`/stats`) - require authentication
- **Authentication Provider**: OIDC via Keycloak
- **Route Protection**: Automatic redirect to sign-in for unauthenticated users accessing protected routes

```mermaid
graph TD
    A[Browser] --> B[React Frontend]
    B --> C[TanStack Router]
    C --> D{Auth Check}
    D -->|Authenticated| E[Search Component]
    D -->|Authenticated| F[Stats Component]
    D -->|Unauthenticated| G[Redirect to Login]
    B --> H[OIDC/Keycloak Auth]
    E --> I[Search API]
    F --> I
    I --> J[(Document Storage)]
    H --> K[Keycloak Server]
```

## Component Structure

```mermaid
graph TD
    A[App] --> B[Router]
    B --> C[SearchLanding]
    B --> D[SearchDocumentCard]
    B --> E[UserModal]
    B --> F[EAOAppBar]
    B --> G[SideNavBar]
    C --> H[SearchResult]
    C --> I[SearchSkeleton]
```

## User Flow & Authentication

### Public Access
- **Home Page** (`/`): Accessible to all users
  - Displays information about environmental assessments
  - Shows "Sign In to Search" button for unauthenticated users
  - Shows "Search" button for authenticated users

### Protected Access (Authentication Required)
- **Search Functionality** (`/search`): Requires authentication
  - Advanced document search with AI strategies
  - Document filtering and results display
  - Automatic redirect to login if not authenticated

- **Statistics Dashboard** (`/stats`): Requires authentication  
  - Usage analytics and metrics
  - Search performance data
  - Automatic redirect to login if not authenticated

### Authentication Flow
```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant K as Keycloak
    
    U->>F: Access /search or /stats
    F->>F: Check authentication
    alt Not Authenticated
        F->>K: Redirect to login
        K->>U: Login form
        U->>K: Enter credentials
        K->>F: Return with auth code
        F->>K: Exchange code for token
        K-->>F: Access token
        F->>F: Store token & user info
        F-->>U: Redirect to requested route
    else Already Authenticated
        F-->>U: Display protected content
    end
```

## Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant S3 as S3 Storage
    participant K as Keycloak

    U->>F: Search Request
    F->>K: Verify Token
    K-->>F: Token Valid
    F->>A: Search Query (with token)
    A->>S3: Fetch Documents
    S3-->>A: Document List
    A-->>F: Search Results
    F-->>U: Display Results
    
    U->>F: View Document
    F->>A: Get Document (with token)
    A->>S3: Fetch PDF
    S3-->>A: PDF Data
    A-->>F: PDF Stream
    F-->>U: Display PDF
```

## Key Features

### Search Functionality

- Real-time search results
- Document preview cards
- Pagination support
- Filter capabilities

### Document Viewing

- In-browser PDF viewing
- Page navigation
- Direct page access
- Secure document access

### Authentication

- KeyCloak integration
- Role-based access control
- Session management

## API Integration

The application communicates with the backend API using Axios. Key endpoints:

- `/api/search` - Search documents
- `/api/document/view` - View document
- `/api/users` - User management

## State Management

The application uses React hooks for state management:

- `useSearch` - Manages search state and results
- `usePlans` - Handles environmental assessment plans
- `useUsers` - Manages user data and interactions

## Security

- Authentication via KeyCloak
- HTTPS enforced
- Secure document access
- Environment-based configuration

## Performance Considerations

- Lazy loading of routes
- PDF streaming
- Response caching
- Optimized search results

## Development Guidelines

### Code Structure

- Components in `src/components`
- Routes in `src/routes`
- Utilities in `src/utils`
- Models in `src/models`
- Styles in `src/styles`

### Best Practices

- TypeScript for type safety
- Component-based architecture
- Consistent error handling
- Environment-based configuration

### Testing

- Unit tests for components
- Integration tests for API calls
- End-to-end testing support

## Deployment

### Environment Configuration for Authentication

The application requires specific environment variables for authentication in different environments:

#### Local Development
```properties
VITE_API_URL=/api
VITE_APP_URL=http://localhost:3000
VITE_OIDC_AUTHORITY=https://dev.loginproxy.gov.bc.ca/auth/realms/eao-epic
VITE_CLIENT_ID=epic-search
PROXY_API_URL=http://127.0.0.1:8081
```

#### Test Environment (Azure App Service)
```properties
VITE_API_URL=/api
VITE_APP_URL=https://your-test-app.azurewebsites.net
VITE_OIDC_AUTHORITY=https://test.loginproxy.gov.bc.ca/auth/realms/eao-epic
VITE_CLIENT_ID=epic-search
PROXY_API_URL=https://your-backend-api-url
```

#### Production Environment (Azure App Service)
```properties
VITE_API_URL=/api
VITE_APP_URL=https://your-prod-app.com
VITE_OIDC_AUTHORITY=https://loginproxy.gov.bc.ca/auth/realms/eao-epic
VITE_CLIENT_ID=epic-search
PROXY_API_URL=https://your-prod-backend-api-url
```

### Keycloak Configuration Requirements

For each environment, the Keycloak client must be configured with:

**Valid Redirect URIs:**
- `{VITE_APP_URL}/oidc-callback`

**Web Origins:**
- `{VITE_APP_URL}`

**Valid Post Logout Redirect URIs:**
- `{VITE_APP_URL}/*`

### Docker Deployment

The application includes a Dockerfile and nginx configuration for containerized deployment with runtime environment variable injection.

```mermaid
graph LR
    A[Source Code] --> B[Node Build]
    B --> C[Nginx Image]
    C --> D[Container]
    D --> E[Runtime Config Generation]
    E --> F[Production Server]
```

### Environment Configuration

- **Development**: `.env` file with dev environment settings
- **Deployment**: Azure App Service environment variables
- **Runtime**: `env.sh` script generates `config.js` from environment variables

## Location-Aware Search

The application includes location detection and forwarding capabilities to enable location-aware search functionality.

### Overview

Users can:
- Enable/disable location detection through the UI
- View their current location (city, region, country)
- Perform location-enhanced searches automatically
- Control location privacy settings with full transparency

### Architecture

#### Components

1. **LocationContext** (`src/contexts/LocationContext.tsx`)
   - React Context provider for global location state management
   - Handles geolocation detection, caching, and permission management
   - Provides hooks for components to access location functionality

2. **LocationControl** (`src/components/Location/LocationControl.tsx`)
   - UI component for location interaction
   - Available in compact mode (app bar) and full mode (search page)
   - Handles user permissions, settings, and manual controls

3. **Axios Integration** (`src/utils/axiosUtils.ts`)
   - Automatically includes location data in search request bodies
   - Validates location data freshness (24-hour expiry)
   - CORS-safe implementation using request body instead of headers

#### Location Data Format

Location data is stored in localStorage and included in search requests:

```json
{
  "latitude": 49.2827,
  "longitude": -123.1207,
  "city": "Vancouver",
  "region": "British Columbia", 
  "country": "Canada",
  "timestamp": "2025-09-22T10:30:00.000Z"
}
```

#### Search Request Integration

Location data is automatically added to search request bodies:

```json
{
  "query": "search term",
  "searchStrategy": "HYBRID_SEMANTIC_FALLBACK",
  "projectIds": ["project1"],
  "userLocation": {
    "latitude": 49.2827,
    "longitude": -123.1207,
    "city": "Vancouver",
    "region": "British Columbia",
    "country": "Canada",
    "timestamp": 1703123456789
  }
}
```

### Privacy & Security

#### User Consent
- Location sharing is **opt-in only**
- Users can easily disable location sharing
- Clear visual indicators show location status
- No location data is sent without explicit user consent

#### Data Handling
- Location data is only cached locally (localStorage)
- No server-side storage of location data
- 24-hour automatic cache expiry
- User can manually clear location data anytime

#### Browser Security
- Requires HTTPS for geolocation API
- Handles permission denied gracefully
- Respects browser geolocation settings
- Falls back gracefully when location is unavailable

### Backend Integration

The backend can access location data from the `userLocation` property in search request bodies:

```javascript
// Example backend handling
const searchRequest = req.body;
if (searchRequest.userLocation) {
  const { latitude, longitude, city, region, country, timestamp } = searchRequest.userLocation;
  
  // Check data freshness (24 hours)
  const locationAge = Date.now() - timestamp;
  const maxAge = 24 * 60 * 60 * 1000;
  
  if (locationAge < maxAge) {
    // Use location data for search enhancement:
    // - Boost results near user location
    // - Filter by proximity
    // - Enhance "near me" queries
  }
}
```

### Configuration

#### Storage Keys
- `epic_search_user_location`: Cached location data
- `epic_search_location_enabled`: User preference for location sharing
- `epic_search_location_permission`: Permission state cache

#### CORS Considerations
- Uses request body instead of custom headers to avoid CORS preflight
- No additional backend CORS configuration required
- Reverse geocoding may be blocked by corporate firewalls (gracefully handled)

## Troubleshooting

Common issues and solutions:

### 1. API Connection Issues
- Check API URL configuration in environment variables
- Verify backend API is running and accessible
- Check network connectivity and firewall settings

### 2. Authentication Issues
- **CORS Errors**: Verify Keycloak client Web Origins configuration
- **Invalid Redirect URI**: Check Keycloak Valid Redirect URIs settings
- **Token Issues**: Verify OIDC Authority URL and Client ID
- **Sign-out Problems**: Check Valid Post Logout Redirect URIs in Keycloak
- **Environment Mismatch**: Ensure VITE_APP_URL matches your deployment URL

### 3. Route Protection Issues
- Verify authentication context is properly configured
- Check beforeLoad functions in protected routes
- Ensure useAuth hook is accessible in components

### 4. Document Viewing Issues
- Verify backend API access and authentication
- Check document permissions and access controls
- Validate PDF viewer compatibility

### 5. Location Feature Issues

**Location not detected:**
- Check browser location permissions
- Ensure HTTPS is used (required for geolocation API)
- Verify geolocation is enabled in browser settings

**Reverse geocoding fails:**
- Expected behavior in some corporate networks
- GPS coordinates still available for search
- City/region names will be empty but functionality preserved

**Location not included in search:**
- Check if location sharing is enabled in UI
- Verify location data hasn't expired (24 hours)
- Check browser console for any errors

### 6. Deployment Issues
- **Config.js not generated**: Check environment variables in deployment platform
- **Authentication redirects to wrong URL**: Verify VITE_APP_URL in deployment
- **Mixed content errors**: Ensure all URLs use HTTPS in production

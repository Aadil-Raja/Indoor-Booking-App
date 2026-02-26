# Frontend Architecture Guide - Sports Court Booking Platform

## Overview
React SPA with Vite featuring two portals: **Owner Portal** and **Customer Portal** (future). Uses React Router, Context API, and Axios.

**Stack**: React • Vite • React Router • Tailwind CSS • Axios

**Backend**: FastAPI with JWT authentication, role-based access (owner/customer)

## Folder Structure

```
Frontend/
├── src/
│   ├── main.jsx              # Entry point - wraps App with Context Providers
│   ├── App.jsx               # Root component - renders routes
│   ├── routes.jsx            # All route definitions
│   ├── assets/               # Static files (images, icons)
│   ├── components/           # Reusable components
│   │   ├── ui/              # UI components (buttons, cards, modals, sidebars)
│   │   └── ProtectedRoute.jsx
│   ├── context/             # Global state management
│   ├── hooks/               # Custom hooks (one per context)
│   ├── pages/               # Page components
│   │   ├── portal-a/       # Portal A pages
│   │   ├── portal-b/       # Portal B pages
│   │   └── auth/           # Auth pages
│   ├── services/            # API layer
│   └── styles/              # Global styles and theme
├── .env                      # Environment variables
├── package.json
├── vite.config.js
└── tailwind.config.js
```

## Main App Flow

### 1. main.jsx - Entry Point
Wraps App with Context Providers in hierarchy:
```jsx
<AuthProviderA>
  <AuthProviderB>
    <DataProvider1>
      <DataProvider2>
        <App />
```

### 2. App.jsx
Renders the routing component

### 3. routes.jsx - Route Definitions
Defines all routes using React Router:
- Auth routes: `/login`, `/signup`, `/verify`, etc.
- Portal A routes: `/portal-a/*` (protected)
- Portal B routes: `/portal-b/*` (protected)
- Default: redirects to login

## Two Portal System

### Portal A (`/portal-a/*`)
**Auth**: OAuth + JWT → `localStorage.tokenA`
**Purpose**: User-facing portal
**Example Routes**:
- `/portal-a/dashboard`
- `/portal-a/items`
- `/portal-a/item/:id`
- `/portal-a/profile`

### Portal B (`/portal-b/*`)
**Auth**: Email/Password → `localStorage.tokenB`
**Purpose**: Admin/management portal
**Example Routes**:
- `/portal-b/dashboard`
- `/portal-b/users`
- `/portal-b/settings`
- `/portal-b/reports`

## Context & Hooks (State Management)

Each context manages specific domain logic. Each has a corresponding hook.

### Pattern
```
context/AuthContext.jsx → hooks/useAuth.js
```

### Example Contexts
- **AuthContext** - Portal A authentication (`user`, `token`, `login()`, `logout()`)
- **AdminAuthContext** - Portal B authentication (`admin`, `token`, `login()`, `logout()`)
- **DataContext** - Business data management
- **NotificationContext** - Real-time notifications

### Usage
```jsx
import { useAuth } from '../hooks/useAuth';

function MyComponent() {
  const { user, login, logout } = useAuth();
  // Use state and methods
}
```

### Context Structure
```jsx
// context/AuthContext.jsx
export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  
  const login = async (email, password) => { /* ... */ };
  const logout = () => { /* ... */ };
  
  return (
    <AuthContext.Provider value={{ user, token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

// hooks/useAuth.js
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
```

## Services (API Layer)

### api.js - Base Axios Instance
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' }
});

// Request Interceptor: Auto-attach token
api.interceptors.request.use((config) => {
  const isPortalB = config.url.startsWith('/portal-b');
  const token = isPortalB 
    ? localStorage.getItem('tokenB')
    : localStorage.getItem('tokenA');
  
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// Response Interceptor: Handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to appropriate login
      const isPortalB = window.location.pathname.startsWith('/portal-b');
      window.location.href = isPortalB ? '/portal-b/login' : '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

### Service Files Pattern
Each service file exports functions for specific API endpoints:

**authService.js** - Authentication
```javascript
import api from './api';

export const login = async (email, password) => {
  const res = await api.post('/auth/login', { email, password });
  return res.data;
};

export const signup = async (userData) => {
  const res = await api.post('/auth/signup', userData);
  return res.data;
};
```

**dataService.js** - Business data
```javascript
export const fetchItems = async () => {
  const res = await api.get('/items');
  return res.data;
};

export const createItem = async (itemData) => {
  const res = await api.post('/items', itemData);
  return res.data;
};
```

### Common Service Files
- `authService.js` - Auth operations
- `userService.js` - User management
- `dataService.js` - Core business data
- `uploadService.js` - File uploads
- `notificationService.js` - Notifications

## Pages

### Portal A Pages
Dashboard, ItemList, ItemDetail, Profile, etc.

### Portal B Pages
Dashboard, UserManagement, Settings, Reports, etc.

### Auth Pages
Login, Signup, VerifyEmail, ForgotPassword, ResetPassword

## Components

### Protected Routes
```jsx
// components/ProtectedRoute.jsx
const ProtectedRoute = ({ children, tokenKey = 'token', redirectTo = '/login' }) => {
  const token = localStorage.getItem(tokenKey);
  return token ? children : <Navigate to={redirectTo} />;
};
```

### UI Components
Organized by category in `components/ui/`:

**Layout**: Sidebar, Header, Footer, Container

**Forms**: Input, Textarea, Select, Button, Checkbox, Radio

**Display**: Card, Table, List, Badge, Avatar, Alert, LoadingSpinner

**Modals**: Modal, Dialog, Drawer, Tooltip

**Navigation**: Navbar, Breadcrumb, Tabs, Pagination

**Feedback**: Toast, ProgressBar, Skeleton

## Environment Variables

Create `.env` file in Frontend root:
```bash
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=MyApp
# Add other variables as needed
```

Access in code:
```javascript
const apiUrl = import.meta.env.VITE_API_URL;
```

## Key Patterns

### 1. Dual Authentication
- Portal A: OAuth + JWT → `localStorage.tokenA`
- Portal B: Email/Password → `localStorage.tokenB`
- Automatic token injection based on route

### 2. Protected Routes
```jsx
<Route path="/portal-a/dashboard" element={
  <ProtectedRoute tokenKey="tokenA" redirectTo="/login">
    <Dashboard />
  </ProtectedRoute>
} />
```

### 3. API Call Pattern
```jsx
const [data, setData] = useState(null);
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);

useEffect(() => {
  const fetchData = async () => {
    setLoading(true);
    try {
      const result = await apiService.getData();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  fetchData();
}, []);
```

### 4. Context Usage
```jsx
import { useAuth } from '../hooks/useAuth';

function MyComponent() {
  const { user, login, logout } = useAuth();
  // Use state and methods
}
```

## Development

### Setup
```bash
cd Frontend
npm install
npm run dev
```

### Build
```bash
npm run build
npm run preview
```

## Best Practices

1. **Component Organization** - Keep components small and focused
2. **State Management** - Use Context for global state, local state when possible
3. **API Calls** - Always use service layer, handle loading/error states
4. **Routing** - Use protected routes, centralized route definitions
5. **Styling** - Use Tailwind utilities, minimal custom CSS
6. **Error Handling** - User-friendly messages, fallback UI

## Adapting to New Projects

1. **Rename portals** - Change portal-a/portal-b to your domain names
2. **Update contexts** - Add/remove contexts based on your needs
3. **Modify services** - Update API endpoints and methods
4. **Customize routes** - Adjust route paths and protection
5. **Update .env** - Add your environment variables
6. **Rebrand UI** - Update theme, colors, and assets

---

This modular architecture allows easy adaptation for different projects while maintaining clean separation of concerns.

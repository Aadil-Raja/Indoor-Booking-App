# Frontend Quick Start Guide

## What We're Building
A sports court booking platform with:
- **Owner Portal**: Manage properties, courts, pricing, bookings
- **Customer Portal** (Future): Browse and book courts

## Your Backend APIs (Summary)

### Authentication
- Signup → Verify Email → Login
- Password login or OTP login
- Password reset flow

### Owner Features
- Dashboard with stats
- Profile management
- Properties CRUD
- Courts CRUD (per property)
- Pricing rules (per court)
- Availability blocking (per court)
- Media uploads (images/videos)
- Booking management (view, confirm, complete)

### Public Features (for customers)
- Search properties (filters: city, sport, price)
- View property/court details
- Check available slots
- Create bookings

## Implementation Order

### ✅ Phase 1: Authentication (START HERE)
**What to build:**
1. Token management utility
2. API service with interceptors
3. Auth context & hook
4. Login page
5. Signup page
6. Email verification page
7. Protected route component

**Key files:**
- `src/utils/tokenManager.js` - Handle localStorage
- `src/services/api.js` - Axios setup with interceptors
- `src/services/authService.js` - Auth API calls
- `src/context/AuthContext.jsx` - Global auth state
- `src/hooks/useAuth.js` - Auth hook
- `src/pages/auth/Login.jsx`
- `src/pages/auth/Signup.jsx`
- `src/components/ProtectedRoute.jsx`

**Test:**
- Signup → Verify → Login → Dashboard
- Logout clears all tokens
- Protected routes work

### Phase 2: Owner Dashboard
**What to build:**
- Dashboard page with stats
- Profile page
- Basic layout (sidebar, header)

**APIs:**
- GET `/owner/dashboard`
- GET/POST `/owner/profile`

### Phase 3: Property Management
**What to build:**
- List properties page
- Create property form
- Edit property page
- Delete property

**APIs:**
- GET `/properties` - List
- POST `/properties` - Create
- GET `/properties/{id}` - Details
- PATCH `/properties/{id}` - Update
- DELETE `/properties/{id}` - Delete

### Phase 4: Court Management
**What to build:**
- List courts (per property)
- Create court form
- Edit court page

**APIs:**
- POST `/properties/{id}/courts`
- GET `/properties/{id}/courts`
- GET/PATCH/DELETE `/courts/{id}`

### Phase 5: Pricing & Availability
**What to build:**
- Pricing rules management
- Time slot blocking calendar

**APIs:**
- POST/GET/PATCH/DELETE `/courts/{id}/pricing`
- POST/GET/DELETE `/courts/{id}/availability`

### Phase 6: Media Management
**What to build:**
- Image upload component
- Gallery view
- Drag & drop reordering

**APIs:**
- POST `/properties/{id}/media`
- POST `/courts/{id}/media`
- GET/PATCH/DELETE `/media/{id}`

### Phase 7: Booking Management
**What to build:**
- Bookings list (with filters)
- Booking detail view
- Confirm/complete actions

**APIs:**
- GET `/bookings` - List owner's bookings
- GET `/bookings/{id}` - Details
- PATCH `/bookings/{id}/confirm`
- PATCH `/bookings/{id}/complete`

### Phase 8: Customer Portal (Future)
**What to build:**
- Browse properties page
- Property detail page
- Booking flow
- My bookings page

**APIs:**
- GET `/public/properties` - Search
- GET `/public/properties/{id}` - Details
- GET `/public/courts/{id}/available-slots`
- POST `/bookings` - Create booking

## Critical Implementation Rules

### 1. Token Management
```javascript
// ALWAYS clear localStorage on login
tokenManager.clearAuth(); // Clear old data
tokenManager.setAuth(token, user); // Set new data
```

### 2. API Interceptor (Auto-attach token)
```javascript
// Already handled in api.js
// Token automatically attached to all requests
// 401 responses automatically redirect to login
```

### 3. Protected Routes
```javascript
<Route path="/owner/dashboard" element={
  <ProtectedRoute requiredRole="owner">
    <Dashboard />
  </ProtectedRoute>
} />
```

### 4. Error Handling Pattern
```javascript
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);

try {
  setLoading(true);
  const result = await service.getData();
  if (result.success) {
    // Handle success
  } else {
    setError(result.message);
  }
} catch (err) {
  setError(err.response?.data?.message || 'Error');
} finally {
  setLoading(false);
}
```

### 5. Backend Response Format
```javascript
{
  success: true/false,
  message: "Success/error message",
  data: { /* actual data */ }
}
```

## Folder Structure
```
Frontend/src/
├── main.jsx                 # Entry point
├── App.jsx                  # Root component
├── routes.jsx               # All routes
├── components/
│   ├── ui/                  # Reusable UI components
│   └── ProtectedRoute.jsx
├── context/
│   └── AuthContext.jsx      # Auth state
├── hooks/
│   └── useAuth.js           # Auth hook
├── pages/
│   ├── auth/                # Login, Signup, etc.
│   └── owner/               # Owner portal pages
├── services/
│   ├── api.js               # Axios instance
│   ├── authService.js       # Auth APIs
│   ├── ownerService.js      # Owner APIs
│   ├── propertyService.js   # Property APIs
│   └── ...                  # Other services
└── utils/
    └── tokenManager.js      # localStorage helper
```

## Environment Setup
```bash
# .env file
VITE_API_URL=http://localhost:8000/api/v1
```

## Quick Commands
```bash
# Install dependencies
cd Frontend
npm install axios react-router-dom

# Run dev server
npm run dev

# Build for production
npm run build
```

## API Base URL
```
http://localhost:8000/api/v1
```

## User Roles
- `owner` - Property owners (your primary focus)
- `customer` - End users who book courts (future)

## Authentication Flow
1. **Signup**: POST `/auth/signup` → Returns success message
2. **Verify Email**: POST `/auth/verify-code` → Verify OTP
3. **Login**: POST `/auth/login/password` → Returns token + user
4. **Store Token**: Save to localStorage
5. **Access Protected Routes**: Token auto-attached to requests

## Next Steps
1. Read `FRONTEND_IMPLEMENTATION_PLAN.md` for detailed code
2. Start with Phase 1 - Authentication
3. Test each phase before moving to next
4. Build incrementally, one feature at a time

## Need Help?
- Check `FRONTEND_IMPLEMENTATION_PLAN.md` for complete code examples
- All backend APIs are documented in the plan
- Follow the phase-by-phase approach
- Test thoroughly at each step

---

**Start with Phase 1 and build the authentication system first!**

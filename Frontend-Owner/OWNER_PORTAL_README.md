# Owner Portal - Quick Guide

## What's Built

A simple owner authentication portal with:
- Owner Signup (with email verification)
- Owner Login
- Protected Owner Dashboard

## How to Run

```bash
cd Frontend
npm run dev
```

The app will run on `http://localhost:5173`

## How to Test

### 1. Signup Flow
1. Go to `http://localhost:5173/signup`
2. Fill in:
   - Full Name
   - Email
   - Password (min 6 characters)
   - Confirm Password
3. Click "Sign Up"
4. Check your email for verification code
5. Enter the 6-digit code
6. Click "Verify Email"

### 2. Login Flow
1. Go to `http://localhost:5173/login`
2. Enter your email and password
3. Click "Login"
4. You'll be redirected to the dashboard

### 3. Dashboard
- View your profile info
- See stats (currently showing 0 for all)
- Logout button in header

## API Endpoints Used

- `POST /api/v1/auth/signup` - Create owner account
- `POST /api/v1/auth/verify-code` - Verify email OTP
- `POST /api/v1/auth/request-code` - Resend OTP
- `POST /api/v1/auth/login/password` - Login with password

## File Structure

```
Frontend/src/
├── components/
│   └── ProtectedRoute.jsx       # Route protection
├── context/
│   └── AuthContext.jsx          # Global auth state
├── hooks/
│   └── useAuth.js               # Auth hook
├── pages/
│   ├── auth/
│   │   ├── Login.jsx            # Login page
│   │   ├── Signup.jsx           # Signup + verification
│   │   └── auth.css             # Auth styles
│   └── owner/
│       ├── Dashboard.jsx        # Owner dashboard
│       └── dashboard.css        # Dashboard styles
├── services/
│   ├── api.js                   # Axios instance
│   └── authService.js           # Auth API calls
├── utils/
│   └── tokenManager.js          # Token storage
├── App.jsx                      # Main app with routes
└── main.jsx                     # Entry point
```

## Features

- Token-based authentication
- Auto-redirect on 401 errors
- Protected routes (owner role required)
- Email verification flow
- Clean, modern UI
- Responsive design

## Next Steps

You can now add:
- Property management pages
- Court management
- Booking management
- Profile settings
- And more owner features!

## Notes

- Backend must be running on `http://localhost:8001`
- Email service must be configured for OTP delivery
- Tokens are stored in localStorage
- Only users with role "owner" can access dashboard

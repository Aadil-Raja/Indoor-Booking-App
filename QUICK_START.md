# Quick Start Guide

## 🚀 Running the Separated Frontends

### Prerequisites
- Node.js installed
- Python 3.8+ installed
- Backend database configured

---

## Step 1: Start Backend

```bash
cd Backend/apps/management
uvicorn app.main:app --reload --port 8001
```

Backend will run on: **http://localhost:8001**

---

## Step 2: Start Frontend-Owner (Port 5173)

Open a new terminal:

```bash
cd Frontend-Owner
npm install  # First time only
npm run dev
```

Owner Portal will run on: **http://localhost:5173**

**Test Owner Portal:**
1. Go to http://localhost:5173/signup
2. Create an owner account
3. Login and access dashboard

---

## Step 3: Start Frontend-Customer (Port 5174)

Open another new terminal:

```bash
cd Frontend-Customer
npm install  # First time only
npm run dev
```

Customer Portal will run on: **http://localhost:5174**

**Test Customer Portal:**
1. Go to http://localhost:5174/signup
2. Create a customer account
3. Login and browse courts

---

## 🎯 What to Test

### Owner Portal (5173)
- ✅ Signup as owner
- ✅ Login
- ✅ Create property
- ✅ Add courts to property
- ✅ Set pricing
- ✅ View dashboard stats

### Customer Portal (5174)
- ✅ Signup as customer
- ✅ Login
- ✅ Browse courts
- ✅ View court details
- ✅ Book a court
- ✅ View bookings

---

## 🔧 Troubleshooting

### Port Already in Use
If you get "port already in use" error:

**For Frontend-Owner (5173):**
```bash
# Kill process on port 5173
npx kill-port 5173
```

**For Frontend-Customer (5174):**
```bash
# Kill process on port 5174
npx kill-port 5174
```

### CORS Errors
Make sure backend CORS includes both ports:
- http://localhost:5173 (Owner)
- http://localhost:5174 (Customer)

### Token Issues
If you have login issues, clear localStorage:
```javascript
// In browser console
localStorage.clear()
```

---

## 📱 Access URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Backend API | http://localhost:8001 | API Server |
| Owner Portal | http://localhost:5173 | Manage Properties |
| Customer Portal | http://localhost:5174 | Book Courts |

---

## 🎉 Success!

You should now have:
- ✅ Backend running on port 8001
- ✅ Owner portal running on port 5173
- ✅ Customer portal running on port 5174
- ✅ Both frontends connecting to the same backend
- ✅ Separate authentication for each portal

Happy coding! 🚀

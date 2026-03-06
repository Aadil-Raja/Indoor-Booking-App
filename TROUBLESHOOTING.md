# Troubleshooting Guide

## Frontend-Customer: "Failed to resolve import 'react-router-dom'"

### Problem
When starting Frontend-Customer, you see:
```
Failed to resolve import "react-router-dom" from "src/App.jsx"
```

### Solution
The dependencies are not installed. Run:

```bash
cd Frontend-Customer
npm install
npm run dev
```

---

## Common Issues

### 1. Missing Dependencies

**Symptoms:**
- Import errors for `react-router-dom`, `axios`, etc.
- Module not found errors

**Solution:**
```bash
# Frontend-Owner
cd Frontend-Owner
npm install

# Frontend-Customer
cd Frontend-Customer
npm install
```

---

### 2. Port Already in Use

**Symptoms:**
```
Port 5173 is already in use
Port 5174 is already in use
```

**Solution:**
```bash
# Kill port 5173 (Owner)
npx kill-port 5173

# Kill port 5174 (Customer)
npx kill-port 5174
```

Or manually find and kill the process:
```bash
# Windows
netstat -ano | findstr :5173
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:5173 | xargs kill -9
```

---

### 3. CORS Errors

**Symptoms:**
```
Access to XMLHttpRequest blocked by CORS policy
```

**Solution:**
1. Make sure backend is running on port 8001
2. Check backend CORS configuration includes both ports:
   - http://localhost:5173
   - http://localhost:5174

**Backend files to check:**
- `Backend/apps/management/app/main.py`
- `Backend/apps/chatbot/app/main.py`

---

### 4. Login/Authentication Issues

**Symptoms:**
- Can't login
- Token errors
- Redirects not working

**Solution:**
```javascript
// Clear localStorage in browser console
localStorage.clear()
```

Then try logging in again.

---

### 5. API Connection Failed

**Symptoms:**
```
Network Error
ERR_CONNECTION_REFUSED
```

**Solution:**
1. Check if backend is running:
   ```bash
   cd Backend/apps/management
   uvicorn app.main:app --reload --port 8001
   ```

2. Check `.env` file in frontend:
   ```
   VITE_API_URL=http://localhost:8001
   ```

3. Restart frontend after changing `.env`:
   ```bash
   npm run dev
   ```

---

### 6. Blank Page / White Screen

**Symptoms:**
- Page loads but shows nothing
- No errors in console

**Solution:**
1. Check browser console for errors (F12)
2. Clear browser cache (Ctrl+Shift+Delete)
3. Hard refresh (Ctrl+Shift+R)
4. Check if all routes are defined in App.jsx

---

### 7. Module Not Found Errors

**Symptoms:**
```
Cannot find module './components/Layout/Sidebar'
```

**Solution:**
1. Check if the file exists at the path
2. Check file name casing (case-sensitive on Linux/Mac)
3. Restart dev server:
   ```bash
   # Stop server (Ctrl+C)
   npm run dev
   ```

---

## Installation Checklist

Before running the applications, ensure:

- [ ] Node.js is installed (v16 or higher)
- [ ] Python 3.8+ is installed
- [ ] Backend dependencies installed
- [ ] Backend database configured
- [ ] Frontend-Owner dependencies installed (`npm install`)
- [ ] Frontend-Customer dependencies installed (`npm install`)
- [ ] `.env` files exist in both frontends
- [ ] Backend is running on port 8001
- [ ] Ports 5173 and 5174 are available

---

## Quick Reset

If everything is broken, try this complete reset:

```bash
# 1. Stop all servers (Ctrl+C in all terminals)

# 2. Clear node_modules and reinstall
cd Frontend-Owner
rm -rf node_modules package-lock.json
npm install

cd ../Frontend-Customer
rm -rf node_modules package-lock.json
npm install

# 3. Clear browser data
# In browser: Ctrl+Shift+Delete -> Clear all

# 4. Restart everything
# Terminal 1: Backend
cd Backend/apps/management
uvicorn app.main:app --reload --port 8001

# Terminal 2: Owner Portal
cd Frontend-Owner
npm run dev

# Terminal 3: Customer Portal
cd Frontend-Customer
npm run dev
```

---

## Still Having Issues?

1. Check all files are saved
2. Check for typos in file paths
3. Check browser console for detailed errors
4. Check terminal for server errors
5. Try restarting your IDE/editor
6. Try restarting your computer (last resort)

---

## Getting Help

When reporting issues, include:
1. Error message (full text)
2. Which frontend (Owner or Customer)
3. What you were trying to do
4. Browser console output
5. Terminal output

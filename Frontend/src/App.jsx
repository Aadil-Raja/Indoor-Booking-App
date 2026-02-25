import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/auth/Login';
import Signup from './pages/auth/Signup';
import Dashboard from './pages/owner/Dashboard';
import OwnerProfile from './pages/owner/OwnerProfile';
import PropertyList from './pages/owner/PropertyList';
import PropertyForm from './pages/owner/PropertyForm';
import PropertyDetails from './pages/owner/PropertyDetails';
import CourtForm from './pages/owner/CourtForm';
import './styles/theme.css';
import './App.css';

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Redirect root to owner login */}
          <Route path="/" element={<Navigate to="/owner/login" replace />} />
          
          {/* Auth Routes - All under /owner */}
          <Route path="/owner/login" element={<Login />} />
          <Route path="/owner/signup" element={<Signup />} />
          
          {/* Protected Owner Routes */}
          <Route 
            path="/owner/dashboard" 
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } 
          />
          
          {/* Phase 1: Owner Profile */}
          <Route 
            path="/owner/profile" 
            element={
              <ProtectedRoute>
                <OwnerProfile />
              </ProtectedRoute>
            } 
          />
          
          {/* Phase 2: Property Management */}
          <Route 
            path="/owner/properties" 
            element={
              <ProtectedRoute>
                <PropertyList />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/owner/properties/new" 
            element={
              <ProtectedRoute>
                <PropertyForm />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/owner/properties/:id" 
            element={
              <ProtectedRoute>
                <PropertyDetails />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/owner/properties/:id/edit" 
            element={
              <ProtectedRoute>
                <PropertyForm />
              </ProtectedRoute>
            } 
          />
          
          {/* Phase 3: Court Management */}
          <Route 
            path="/owner/properties/:propertyId/courts/new" 
            element={
              <ProtectedRoute>
                <CourtForm />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/owner/courts/:id/edit" 
            element={
              <ProtectedRoute>
                <CourtForm />
              </ProtectedRoute>
            } 
          />
          
          {/* Phase 4: Pricing & Availability */}
          {/* <Route path="/owner/courts/:id/pricing" element={<ProtectedRoute><CourtPricing /></ProtectedRoute>} /> */}
          {/* <Route path="/owner/courts/:id/availability" element={<ProtectedRoute><CourtAvailability /></ProtectedRoute>} /> */}
          
          {/* Phase 5: Booking Management */}
          {/* <Route path="/owner/bookings" element={<ProtectedRoute><BookingList /></ProtectedRoute>} /> */}
          {/* <Route path="/owner/bookings/:id" element={<ProtectedRoute><BookingDetails /></ProtectedRoute>} /> */}
          
          {/* Fallback - redirect unknown routes to dashboard */}
          <Route path="*" element={<Navigate to="/owner/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;

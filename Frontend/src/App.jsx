import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Auth from './pages/auth/Auth';
import Dashboard from './pages/owner/Dashboard';
import OwnerProfile from './pages/owner/OwnerProfile';
import PropertyList from './pages/owner/PropertyList';
import PropertyForm from './pages/owner/PropertyForm';
import PropertyDetails from './pages/owner/PropertyDetails';
import CourtList from './pages/owner/CourtList';
import CourtForm from './pages/owner/CourtForm';
import CourtDetails from './pages/owner/CourtDetails';
import ChatbotTest from './pages/customer/ChatbotTest';
import './styles/theme.css';
import './styles/common.css';
import './App.css';

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Redirect root to auth */}
          <Route path="/" element={<Navigate to="/auth" replace />} />
          
          {/* Auth Routes - Unified login/signup page */}
          <Route path="/auth" element={<Auth />} />
          <Route path="/owner/login" element={<Navigate to="/auth" replace />} />
          <Route path="/owner/signup" element={<Navigate to="/auth" replace />} />
          
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
            path="/owner/courts" 
            element={
              <ProtectedRoute>
                <CourtList />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/owner/properties/:propertyId/courts/new" 
            element={
              <ProtectedRoute>
                <CourtForm />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/owner/courts/:id" 
            element={
              <ProtectedRoute>
                <CourtDetails />
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
          
          {/* Chatbot Test Interface - No auth required for testing */}
          <Route path="/chatbot-test" element={<ChatbotTest />} />
          
          {/* Fallback - redirect unknown routes to dashboard */}
          <Route path="*" element={<Navigate to="/owner/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;

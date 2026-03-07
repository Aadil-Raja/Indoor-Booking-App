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
import CourtList from './pages/owner/CourtList';
import CourtForm from './pages/owner/CourtForm';
import CourtDetails from './pages/owner/CourtDetails';
import './styles/theme.css';
import './styles/common.css';
import './App.css';

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Redirect root to login */}
          <Route path="/" element={<Navigate to="/login" replace />} />

          {/* Auth Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />

          {/* Protected Owner Routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />

          {/* Owner Profile */}
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <OwnerProfile />
              </ProtectedRoute>
            }
          />

          {/* Property Management */}
          <Route
            path="/properties"
            element={
              <ProtectedRoute>
                <PropertyList />
              </ProtectedRoute>
            }
          />
          <Route
            path="/properties/new"
            element={
              <ProtectedRoute>
                <PropertyForm />
              </ProtectedRoute>
            }
          />
          <Route
            path="/properties/:id"
            element={
              <ProtectedRoute>
                <PropertyDetails />
              </ProtectedRoute>
            }
          />
          <Route
            path="/properties/:id/edit"
            element={
              <ProtectedRoute>
                <PropertyForm />
              </ProtectedRoute>
            }
          />

          {/* Court Management */}
          <Route
            path="/courts"
            element={
              <ProtectedRoute>
                <CourtList />
              </ProtectedRoute>
            }
          />
          <Route
            path="/properties/:propertyId/courts/new"
            element={
              <ProtectedRoute>
                <CourtForm />
              </ProtectedRoute>
            }
          />
          <Route
            path="/courts/:id"
            element={
              <ProtectedRoute>
                <CourtDetails />
              </ProtectedRoute>
            }
          />
          <Route
            path="/courts/:id/edit"
            element={
              <ProtectedRoute>
                <CourtForm />
              </ProtectedRoute>
            }
          />

          {/* Fallback - redirect unknown routes to dashboard */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;

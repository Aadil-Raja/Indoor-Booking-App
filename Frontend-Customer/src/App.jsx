import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/auth/Login';
import Signup from './pages/auth/Signup';
import UserDashboard from './pages/user/UserDashboard';
import CourtDetails from './pages/user/CourtDetails';
import BookCourt from './pages/user/BookCourt';
import UserBookings from './pages/user/UserBookings';
import UserProfile from './pages/user/UserProfile';
import ChatbotTest from './pages/customer/ChatbotTest';
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
          
          {/* Protected Customer Routes */}
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute>
                <UserDashboard />
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
            path="/courts/:id/book" 
            element={
              <ProtectedRoute>
                <BookCourt />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/bookings" 
            element={
              <ProtectedRoute>
                <UserBookings />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/profile" 
            element={
              <ProtectedRoute>
                <UserProfile />
              </ProtectedRoute>
            } 
          />
          
          {/* Chatbot Test Route */}
          <Route 
            path="/chatbot-test" 
            element={<ChatbotTest />} 
          />
          
          {/* Fallback - redirect unknown routes to dashboard */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;

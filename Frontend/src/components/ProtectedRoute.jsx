import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const ProtectedRoute = ({ children, requiredRole }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/owner/login" replace />;
  }

  // Since we only store token, we assume all authenticated users are owners
  // Backend will validate the actual role via JWT token

  return children;
};

export default ProtectedRoute;

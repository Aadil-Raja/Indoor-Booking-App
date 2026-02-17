import { useAuth } from '../../hooks/useAuth';
import { useNavigate } from 'react-router-dom';
import './dashboard.css';

const Dashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>Owner Dashboard</h1>
        <button onClick={handleLogout} className="btn-logout">
          Logout
        </button>
      </header>

      <div className="dashboard-content">
        <div className="welcome-card">
          <h2>Welcome, {user?.name}!</h2>
          <p>Email: {user?.email}</p>
          <p>Role: {user?.role}</p>
        </div>

        <div className="dashboard-grid">
          <div className="dashboard-card">
            <h3>Properties</h3>
            <p className="card-number">0</p>
            <p className="card-label">Total Properties</p>
          </div>

          <div className="dashboard-card">
            <h3>Courts</h3>
            <p className="card-number">0</p>
            <p className="card-label">Total Courts</p>
          </div>

          <div className="dashboard-card">
            <h3>Bookings</h3>
            <p className="card-number">0</p>
            <p className="card-label">Total Bookings</p>
          </div>

          <div className="dashboard-card">
            <h3>Revenue</h3>
            <p className="card-number">₹0</p>
            <p className="card-label">Total Revenue</p>
          </div>
        </div>

        <div className="info-section">
          <h3>Getting Started</h3>
          <ul>
            <li>Add your first property</li>
            <li>Create courts for your property</li>
            <li>Set pricing and availability</li>
            <li>Start receiving bookings</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

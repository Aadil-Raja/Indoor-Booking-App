import { useAuth } from '../../hooks/useAuth';
import { useNavigate, Link } from 'react-router-dom';
import './dashboard.css';

const Dashboard = () => {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/owner/login');
  };

  return (
    <div className="ib-owner-dashboard">
      <header className="ib-owner-header">
        <h1>Owner Dashboard</h1>
        <button onClick={handleLogout} className="ib-owner-btn-logout">
          Logout
        </button>
      </header>

      <div className="ib-owner-content">
        <div className="ib-owner-welcome-card">
          <h2>Welcome to Indoor Booking!</h2>
          <p>Manage your properties, courts, and bookings from here.</p>
        </div>

        <div className="ib-owner-stats-grid">
          <div className="ib-owner-stat-card">
            <h3>Properties</h3>
            <span className="ib-owner-stat-number">0</span>
            <span className="ib-owner-stat-label">Total Properties</span>
          </div>

          <div className="ib-owner-stat-card">
            <h3>Courts</h3>
            <span className="ib-owner-stat-number">0</span>
            <span className="ib-owner-stat-label">Total Courts</span>
          </div>

          <div className="ib-owner-stat-card">
            <h3>Bookings</h3>
            <span className="ib-owner-stat-number">0</span>
            <span className="ib-owner-stat-label">Total Bookings</span>
          </div>

          <div className="ib-owner-stat-card">
            <h3>Revenue</h3>
            <span className="ib-owner-stat-number">₹0</span>
            <span className="ib-owner-stat-label">Total Revenue</span>
          </div>
        </div>

        <div className="ib-owner-info-section">
          <h3>Quick Actions</h3>
          <ul>
            <li>
              <Link to="/owner/profile" style={{ textDecoration: 'none', color: 'inherit' }}>
                Complete your profile
              </Link>
            </li>
            <li>
              <Link to="/owner/properties" style={{ textDecoration: 'none', color: 'inherit' }}>
                Manage properties
              </Link>
            </li>
            <li>
              <Link to="/owner/properties/new" style={{ textDecoration: 'none', color: 'inherit' }}>
                Add your first property
              </Link>
            </li>
            <li>Set pricing and availability (Phase 4)</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

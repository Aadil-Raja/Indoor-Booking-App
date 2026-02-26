import { Link } from 'react-router-dom';
import OwnerLayout from '../../components/Layout/OwnerLayout';
import './dashboard.css';

const Dashboard = () => {
  return (
    <OwnerLayout>
      <div className="ib-dashboard">
        <div className="ib-dashboard-header">
          <div>
            <h1>Dashboard</h1>
            <p>Welcome back! Here's an overview of your business.</p>
          </div>
        </div>

        <div className="ib-dashboard-content">
          {/* Stats Grid */}
          <div className="ib-dashboard-stats">
            <Link to="/owner/properties" className="ib-dashboard-stat-card">
              <div className="ib-stat-icon">▣</div>
              <div className="ib-stat-content">
                <div className="ib-stat-number">0</div>
                <div className="ib-stat-label">Properties</div>
              </div>
            </Link>

            <div className="ib-dashboard-stat-card">
              <div className="ib-stat-icon">⚐</div>
              <div className="ib-stat-content">
                <div className="ib-stat-number">0</div>
                <div className="ib-stat-label">Courts</div>
              </div>
            </div>

            <div className="ib-dashboard-stat-card">
              <div className="ib-stat-icon">◷</div>
              <div className="ib-stat-content">
                <div className="ib-stat-number">0</div>
                <div className="ib-stat-label">Bookings</div>
              </div>
            </div>

            <div className="ib-dashboard-stat-card">
              <div className="ib-stat-icon">₹</div>
              <div className="ib-stat-content">
                <div className="ib-stat-number">₹0</div>
                <div className="ib-stat-label">Revenue</div>
              </div>
            </div>
          </div>

          {/* Get Started Section */}
          <div className="ib-dashboard-card">
            <h2>Get Started</h2>
            <p style={{ color: 'var(--color-gray-600)', marginBottom: 'var(--spacing-lg)' }}>
              Follow these steps to set up your indoor booking business
            </p>
            <div className="ib-dashboard-steps">
              <div className="ib-dashboard-step">
                <div className="ib-step-number">1</div>
                <div className="ib-step-content">
                  <h3>Complete Your Profile</h3>
                  <p>Add your business information</p>
                  <Link to="/owner/profile" className="ib-step-link">
                    Go to Profile →
                  </Link>
                </div>
              </div>

              <div className="ib-dashboard-step">
                <div className="ib-step-number">2</div>
                <div className="ib-step-content">
                  <h3>Add Your First Property</h3>
                  <p>Create a property to manage courts</p>
                  <Link to="/owner/properties/new" className="ib-step-link">
                    Add Property →
                  </Link>
                </div>
              </div>

              <div className="ib-dashboard-step">
                <div className="ib-step-number">3</div>
                <div className="ib-step-content">
                  <h3>Add Courts & Set Pricing</h3>
                  <p>Configure your courts and pricing rules</p>
                  <Link to="/owner/properties" className="ib-step-link">
                    Manage Properties →
                  </Link>
                </div>
              </div>
            </div>
          </div>

          {/* Recent Activity */}
          <div className="ib-dashboard-card">
            <h2>Recent Bookings</h2>
            <div className="ib-dashboard-empty">
              <p>No bookings yet</p>
              <p style={{ fontSize: '14px', color: 'var(--color-gray-500)' }}>
                Bookings will appear here once customers start booking your courts
              </p>
            </div>
          </div>
        </div>
      </div>
    </OwnerLayout>
  );
};

export default Dashboard;

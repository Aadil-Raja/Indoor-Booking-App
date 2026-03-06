import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import OwnerLayout from '../../components/Layout/OwnerLayout';
import { ownerService } from '../../services/ownerService';
import './dashboard.css';
import './dashboardNew.css';

const Dashboard = () => {
  const [stats, setStats] = useState({
    properties_count: 0,
    courts_count: 0,
    bookings_count: 0,
    total_revenue: 0
  });
  const [loading, setLoading] = useState(true);
  const [recentBookings, setRecentBookings] = useState([]);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const result = await ownerService.getDashboardStats();
      
      if (result.success && result.data) {
        // Backend returns data in nested 'stats' object
        const statsData = result.data.stats || {};
        
        setStats({
          properties_count: statsData.total_properties || 0,
          courts_count: statsData.total_courts || 0,
          bookings_count: statsData.total_bookings || 0,
          total_revenue: statsData.total_revenue || 0
        });
        
        // Set recent bookings if available
        if (result.data.recent_bookings) {
          setRecentBookings(result.data.recent_bookings);
        }
      }
    } catch (err) {
      console.error('Failed to load dashboard stats:', err);
    } finally {
      setLoading(false);
    }
  };

  // Format price with comma
  const formatPrice = (price) => {
    return price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  };

  // Format date
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric' 
    });
  };

  // Format time
  const formatTime = (timeString) => {
    return timeString.substring(0, 5); // "07:00:00" -> "07:00"
  };

  return (
    <OwnerLayout>
      <div className="ch-dashboard">
        {/* Topbar */}
        <div className="ch-topbar">
          <div className="ch-topbar-left">
            <h1 className="ch-page-title">Dashboard</h1>
            <p className="ch-page-subtitle">Welcome back! Here's an overview of your business.</p>
          </div>
        </div>

        <div className="ch-content">
          {/* Stats Grid */}
          <div className="ch-dashboard-stats">
            <Link to="/properties" className="ch-stat-card ch-stat-clickable">
              <div className="ch-stat-icon ch-stat-icon-green">🏢</div>
              <div className="ch-stat-content">
                <div className="ch-stat-number">
                  {loading ? '...' : stats.properties_count}
                </div>
                <div className="ch-stat-label">Properties</div>
              </div>
            </Link>

            <Link to="/courts" className="ch-stat-card ch-stat-clickable">
              <div className="ch-stat-icon ch-stat-icon-blue">🏟️</div>
              <div className="ch-stat-content">
                <div className="ch-stat-number">
                  {loading ? '...' : stats.courts_count}
                </div>
                <div className="ch-stat-label">Courts</div>
              </div>
            </Link>

            <div className="ch-stat-card">
              <div className="ch-stat-icon ch-stat-icon-purple">📅</div>
              <div className="ch-stat-content">
                <div className="ch-stat-number">
                  {loading ? '...' : stats.bookings_count}
                </div>
                <div className="ch-stat-label">Bookings</div>
              </div>
            </div>

            <div className="ch-stat-card">
              <div className="ch-stat-icon ch-stat-icon-amber">💰</div>
              <div className="ch-stat-content">
                <div className="ch-stat-number">
                  {loading ? '...' : `PKR ${formatPrice(stats.total_revenue)}`}
                </div>
                <div className="ch-stat-label">Total Revenue</div>
              </div>
            </div>
          </div>

          {/* Get Started Section - Only show if no properties */}
          {!loading && stats.properties_count === 0 && (
            <div className="ch-dashboard-card">
              <h2 className="ch-card-title">Get Started</h2>
              <p className="ch-card-subtitle">
                Follow these steps to set up your indoor booking business
              </p>
              <div className="ch-dashboard-steps">
                <div className="ch-dashboard-step">
                  <div className="ch-step-number">1</div>
                  <div className="ch-step-content">
                    <h3>Complete Your Profile</h3>
                    <p>Add your business information</p>
                    <Link to="/profile" className="ch-step-link">
                      Go to Profile →
                    </Link>
                  </div>
                </div>

                <div className="ch-dashboard-step">
                  <div className="ch-step-number">2</div>
                  <div className="ch-step-content">
                    <h3>Add Your First Property</h3>
                    <p>Create a property to manage courts</p>
                    <Link to="/properties/new" className="ch-step-link">
                      Add Property →
                    </Link>
                  </div>
                </div>

                <div className="ch-dashboard-step">
                  <div className="ch-step-number">3</div>
                  <div className="ch-step-content">
                    <h3>Add Courts & Set Pricing</h3>
                    <p>Configure your courts and pricing rules</p>
                    <Link to="/properties" className="ch-step-link">
                      Manage Properties →
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Recent Bookings */}
          <div className="ch-dashboard-card">
            <div className="ch-card-header">
              <div>
                <h2 className="ch-card-title">Recent Bookings</h2>
                {recentBookings.length > 0 && (
                  <span className="ch-pricing-badge">{recentBookings.length} bookings</span>
                )}
              </div>
              {recentBookings.length > 0 && (
                <Link to="/bookings" className="ch-btn-ghost">
                  View All →
                </Link>
              )}
            </div>

            {loading ? (
              <div className="ch-pricing-loading">Loading bookings...</div>
            ) : recentBookings.length === 0 ? (
              <div className="ch-pricing-empty">
                <div className="ch-pricing-empty-icon">📅</div>
                <h3>No bookings yet</h3>
                <p>Bookings will appear here once customers start booking your courts</p>
              </div>
            ) : (
              <div className="ch-bookings-list">
                {recentBookings.map((booking) => (
                  <div key={booking.id} className="ch-booking-card">
                    <div className="ch-booking-accent"></div>
                    
                    <div className="ch-booking-body">
                      {/* Booking Info */}
                      <div className="ch-booking-meta">
                        <div className="ch-booking-label">
                          📅 BOOKING #{booking.id}
                        </div>
                        
                        <div className="ch-booking-court">
                          <span className="ch-booking-court-name">{booking.court_name}</span>
                          <span className="ch-booking-property">at {booking.property_name}</span>
                        </div>

                        <div className="ch-booking-time-row">
                          <span className="ch-booking-date">📆 {formatDate(booking.booking_date)}</span>
                          <span className="ch-booking-time">
                            🕐 {formatTime(booking.start_time)} – {formatTime(booking.end_time)}
                          </span>
                        </div>
                      </div>

                      {/* Customer Info */}
                      <div className="ch-booking-customer">
                        <div className="ch-booking-customer-label">CUSTOMER</div>
                        <div className="ch-booking-customer-name">
                          {booking.customer_name || 'N/A'}
                        </div>
                      </div>

                      {/* Price & Status */}
                      <div className="ch-booking-right">
                        <div className="ch-booking-price">PKR {formatPrice(booking.total_price)}</div>
                        <span className={`ch-booking-status ch-booking-status-${booking.status.toLowerCase()}`}>
                          {booking.status}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </OwnerLayout>
  );
};

export default Dashboard;

import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import './sidebar.css';

const Sidebar = () => {
  const location = useLocation();
  const { logout } = useAuth();

  const isActive = (path) => {
    if (path === '/owner/dashboard') {
      return location.pathname === path;
    }
    return location.pathname.startsWith(path);
  };

  const handleLogout = () => {
    if (window.confirm('Are you sure you want to logout?')) {
      logout();
    }
  };

  return (
    <aside className="ch-sidebar">
      {/* Sport emoji watermark background */}
      <div className="ch-sidebar-watermark">
        {['🏏', '⚽', '🎾', '🏸', '🏀', '🏐'].map((emoji, i) => (
          <span key={i} className="ch-sidebar-watermark-emoji">{emoji}</span>
        ))}
      </div>

      {/* Brand section */}
      <div className="ch-sidebar-brand">
        <div className="ch-sidebar-logo">
          <div className="ch-sidebar-logo-icon">⚽</div>
          <div className="ch-sidebar-logo-text">
            <span className="ch-sidebar-logo-court">Court</span>
            <span className="ch-sidebar-logo-hub">Hub</span>
          </div>
        </div>
        <p className="ch-sidebar-portal-label">OWNER PORTAL</p>
      </div>

      {/* Navigation */}
      <nav className="ch-sidebar-nav">
        <Link
          to="/owner/dashboard"
          className={`ch-sidebar-link ${isActive('/owner/dashboard') ? 'active' : ''}`}
        >
          <span className="ch-sidebar-icon">📊</span>
          <span className="ch-sidebar-text">Dashboard</span>
        </Link>

        <Link
          to="/owner/properties"
          className={`ch-sidebar-link ${isActive('/owner/properties') ? 'active' : ''}`}
        >
          <span className="ch-sidebar-icon">🏢</span>
          <span className="ch-sidebar-text">Properties</span>
        </Link>

        <Link
          to="/owner/courts"
          className={`ch-sidebar-link ${isActive('/owner/courts') ? 'active' : ''}`}
        >
          <span className="ch-sidebar-icon">🏟️</span>
          <span className="ch-sidebar-text">Courts</span>
        </Link>

        <div className="ch-sidebar-divider"></div>

        <Link
          to="/owner/bookings"
          className={`ch-sidebar-link ${isActive('/owner/bookings') ? 'active' : ''}`}
        >
          <span className="ch-sidebar-icon">📅</span>
          <span className="ch-sidebar-text">Bookings</span>
        </Link>

        <Link
          to="/owner/profile"
          className={`ch-sidebar-link ${isActive('/owner/profile') ? 'active' : ''}`}
        >
          <span className="ch-sidebar-icon">👤</span>
          <span className="ch-sidebar-text">Profile</span>
        </Link>
      </nav>

      {/* Footer with logout */}
      <div className="ch-sidebar-footer">
        <button onClick={handleLogout} className="ch-sidebar-link ch-sidebar-logout">
          <span className="ch-sidebar-icon">⏻</span>
          <span className="ch-sidebar-text">Logout</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;

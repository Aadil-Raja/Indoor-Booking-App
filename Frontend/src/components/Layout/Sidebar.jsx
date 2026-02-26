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
    <aside className="ib-sidebar">
      <div className="ib-sidebar-header">
        <h2>Indoor Booking</h2>
        <p>Owner Portal</p>
      </div>

      <nav className="ib-sidebar-nav">
        <Link
          to="/owner/dashboard"
          className={`ib-sidebar-link ${isActive('/owner/dashboard') ? 'active' : ''}`}
        >
          <span className="ib-sidebar-icon">📊</span>
          <span className="ib-sidebar-text">Dashboard</span>
        </Link>

        <Link
          to="/owner/properties"
          className={`ib-sidebar-link ${isActive('/owner/properties') ? 'active' : ''}`}
        >
          <span className="ib-sidebar-icon">🏢</span>
          <span className="ib-sidebar-text">Properties</span>
        </Link>

        <Link
          to="/owner/courts"
          className={`ib-sidebar-link ${isActive('/owner/courts') ? 'active' : ''}`}
        >
          <span className="ib-sidebar-icon">⚐</span>
          <span className="ib-sidebar-text">Courts</span>
        </Link>

        <Link
          to="/owner/profile"
          className={`ib-sidebar-link ${isActive('/owner/profile') ? 'active' : ''}`}
        >
          <span className="ib-sidebar-icon">👤</span>
          <span className="ib-sidebar-text">Profile</span>
        </Link>

        <div className="ib-sidebar-divider"></div>

        <button onClick={handleLogout} className="ib-sidebar-link ib-sidebar-logout">
          <span className="ib-sidebar-icon">⏻</span>
          <span className="ib-sidebar-text">Logout</span>
        </button>
      </nav>

      <div className="ib-sidebar-footer">
        <p>© 2024 Indoor Booking</p>
      </div>
    </aside>
  );
};

export default Sidebar;

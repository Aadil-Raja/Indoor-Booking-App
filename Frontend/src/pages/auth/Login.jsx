import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authService } from '../../services/authService';
import { useAuth } from '../../hooks/useAuth';
import './auth.css';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await authService.loginPassword(email, password);

      if (result.success) {
        // Backend returns: { access_token, token_type, name }
        login(result.data.access_token);
        navigate('/owner/dashboard');
      } else {
        setError(result.message || 'Login failed');
      }
    } catch (err) {
      setError(
        err.response?.data?.message || 'Login failed. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ib-auth-container">
      <div className="ib-auth-card">
        <h1>Owner Login</h1>
        <p className="ib-auth-subtitle">Sign in to manage your properties</p>
        
        {error && <div className="ib-auth-error-message">{error}</div>}
        
        <form onSubmit={handleSubmit}>
          <div className="ib-auth-form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="Enter your email"
            />
          </div>

          <div className="ib-auth-form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Enter your password"
            />
          </div>

          <button type="submit" className="ib-auth-btn-primary" disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <div className="ib-auth-footer">
          <p>Don't have an account? <Link to="/owner/signup">Sign up</Link></p>
        </div>
      </div>
    </div>
  );
};

export default Login;

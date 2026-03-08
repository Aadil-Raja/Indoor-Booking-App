import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../../services/authService';
import { useAuth } from '../../hooks/useAuth';
import './auth.css';

const Login = () => {
  const [loginPanel, setLoginPanel] = useState('main');
  const [loginData, setLoginData] = useState({ email: '', password: '' });
  const [otpCode, setOtpCode] = useState(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleOtpChange = (index, value) => {
    if (value.length > 1) value = value[0];
    if (!/^\d*$/.test(value)) return;

    const newOtp = [...otpCode];
    newOtp[index] = value;
    setOtpCode(newOtp);

    if (value && index < 5) {
      const nextInput = document.getElementById(`otp-${index + 1}`);
      if (nextInput) nextInput.focus();
    }
  };

  const handleOtpKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !e.target.value && index > 0) {
      const prevInput = document.getElementById(`otp-${index - 1}`);
      if (prevInput) prevInput.focus();
    }
  };

  const handlePasswordLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await authService.loginPassword(loginData.email, loginData.password);
      if (result.success) {
        login(result.data.access_token);
        navigate('/dashboard');
      } else {
        setError(result.message || 'Login failed');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleRequestOtp = async () => {
    if (!loginData.email) {
      setError('Please enter your email first');
      return;
    }
    setError('');
    setLoading(true);

    try {
      const result = await authService.requestLoginCode(loginData.email);
      if (result.success) {
        setLoginPanel('otp');
      } else {
        setError(result.message || 'Failed to send OTP');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleOtpLogin = async (e) => {
    e.preventDefault();
    const code = otpCode.join('');
    if (code.length !== 6) {
      setError('Please enter all 6 digits');
      return;
    }
    setError('');
    setLoading(true);

    try {
      const result = await authService.verifyLoginCode(loginData.email, code);
      if (result.success) {
        login(result.data.access_token);
        navigate('/dashboard');
      } else {
        setError(result.message || 'Invalid code');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  const handleResendCode = async () => {
    setError('');
    setLoading(true);

    try {
      const result = await authService.requestCode(loginData.email);
      if (result.success) {
        alert('Code resent to your email');
      } else {
        setError(result.message || 'Failed to resend code');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to resend code');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ch-shell" data-view="login">
      <div className="ch-visual-panel">
        <div className="ch-emoji-grid">
          {Array.from({ length: 42 }).map((_, i) => (
            <div key={i} className="ch-emoji-cell">
              {['🏏', '⚽', '🎾', '🏸', '🏀', '🏐'][i % 6]}
            </div>
          ))}
        </div>
        <div className="ch-gradient-overlay"></div>
        <div className="ch-fade-bottom"></div>
        
        <div className="ch-visual-content">
          <div className="ch-logo-row">
            <div className="ch-logo-icon">⚽</div>
            <div className="ch-logo-text">
              <span className="ch-logo-court">Court</span>
              <span className="ch-logo-hub">Hub</span>
            </div>
          </div>

          <div className="ch-badge">
            <span className="ch-badge-dot"></span>
            <span className="ch-badge-text">Live Bookings</span>
          </div>

          <h1 className="ch-hero-title">
            Play More,<br /><span className="accent">Book Smarter.</span>
          </h1>

          <p className="ch-hero-subtitle">
            Discover and book premium indoor sports venues across your city in seconds
          </p>

          <div className="ch-sport-tags">
            {[
              { emoji: '🏏', name: 'Cricket' },
              { emoji: '⚽', name: 'Football' },
              { emoji: '🎾', name: 'Tennis' },
              { emoji: '🏸', name: 'Badminton' },
              { emoji: '🏀', name: 'Basketball' },
              { emoji: '🏐', name: 'Volleyball' }
            ].map((sport) => (
              <div key={sport.name} className="ch-sport-tag">
                <span>{sport.emoji}</span>
                <span>{sport.name}</span>
              </div>
            ))}
          </div>

          <div className="ch-cta-row">
            <span className="ch-cta-text">New here?</span>
            <button className="ch-cta-btn" onClick={() => navigate('/signup')}>
              Create Account →
            </button>
          </div>
        </div>
      </div>

      <div className="ch-form-panel">
        <div className="ch-emoji-watermark">
          {Array.from({ length: 42 }).map((_, i) => (
            <div key={i} className="ch-emoji-cell">
              {['🏏', '⚽', '🎾', '🏸', '🏀', '🏐'][i % 6]}
            </div>
          ))}
        </div>

        <div className="ch-form-content">
          <div className="ch-form-viewport">
            {loginPanel === 'main' ? (
              <div className="ch-form-inner active">
                <h2 className="ch-form-title">Welcome back</h2>
                <p className="ch-form-subtitle">Sign in to book your next game</p>

                {error && <div className="ch-error-box">{error}</div>}

                <form onSubmit={handlePasswordLogin}>
                  <div className="ch-field">
                    <label>EMAIL</label>
                    <input
                      type="email"
                      value={loginData.email}
                      onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                      placeholder="your@email.com"
                      required
                    />
                  </div>

                  <div className="ch-field">
                    <label>PASSWORD</label>
                    <input
                      type="password"
                      value={loginData.password}
                      onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                      placeholder="Enter password"
                      required
                    />
                    <a href="#" className="ch-forgot-link">Forgot password?</a>
                  </div>

                  <button type="submit" className="ch-btn-primary" disabled={loading}>
                    {loading ? 'Signing in...' : 'Sign In →'}
                  </button>
                </form>

                <div className="ch-divider">
                  <span>or</span>
                </div>

                <button className="ch-btn-outline" onClick={handleRequestOtp} disabled={loading}>
                  📱 Sign in with OTP Code
                </button>

                <p className="ch-bottom-note">
                  New to CourtHub? <button onClick={() => navigate('/signup')}>Create account</button>
                </p>
              </div>
            ) : (
              <div className="ch-form-inner active">
                <div className="ch-icon-box">📲</div>
                <h2 className="ch-form-title">Enter OTP Code</h2>
                <p className="ch-form-subtitle">We sent a 6-digit code to {loginData.email}</p>

                {error && <div className="ch-error-box">{error}</div>}

                <form onSubmit={handleOtpLogin}>
                  <div className="ch-otp-row">
                    {otpCode.map((digit, index) => (
                      <input
                        key={index}
                        id={`otp-${index}`}
                        type="text"
                        maxLength="1"
                        value={digit}
                        onChange={(e) => handleOtpChange(index, e.target.value)}
                        onKeyDown={(e) => handleOtpKeyDown(index, e)}
                        className="ch-otp-box"
                      />
                    ))}
                  </div>

                  <button type="submit" className="ch-btn-primary" disabled={loading}>
                    {loading ? 'Verifying...' : 'Verify & Sign In →'}
                  </button>
                </form>

                <button className="ch-btn-outline" onClick={() => setLoginPanel('main')}>
                  ← Back
                </button>

                <p className="ch-resend-note">
                  Didn't receive code? <button onClick={handleResendCode}>Resend</button>
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;

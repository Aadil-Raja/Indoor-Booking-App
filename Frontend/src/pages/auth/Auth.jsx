import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../../services/authService';
import { useAuth } from '../../hooks/useAuth';
import './auth.css';

const Auth = () => {
  const [activeView, setActiveView] = useState('login'); // 'login' or 'signup'
  const [loginPanel, setLoginPanel] = useState('main'); // 'main' or 'otp'
  const [signupPanel, setSignupPanel] = useState('form'); // 'form' or 'verify'
  
  const [loginData, setLoginData] = useState({ email: '', password: '' });
  const [signupData, setSignupData] = useState({ firstName: '', lastName: '', email: '', phone: '', password: '' });
  const [otpCode, setOtpCode] = useState(['', '', '', '', '', '']);
  const [verifyCode, setVerifyCode] = useState(['', '', '', '', '', '']);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const navigate = useNavigate();
  const { login } = useAuth();

  // Switch between login and signup
  const switchView = (view) => {
    setActiveView(view);
    setError('');
    setLoginPanel('main');
    setSignupPanel('form');
  };

  // Handle OTP input
  const handleOtpChange = (index, value, isVerify = false) => {
    if (value.length > 1) value = value[0];
    if (!/^\d*$/.test(value)) return;

    const newOtp = isVerify ? [...verifyCode] : [...otpCode];
    newOtp[index] = value;
    
    if (isVerify) {
      setVerifyCode(newOtp);
    } else {
      setOtpCode(newOtp);
    }

    // Auto-focus next input
    if (value && index < 5) {
      const nextInput = document.getElementById(`${isVerify ? 'verify' : 'otp'}-${index + 1}`);
      if (nextInput) nextInput.focus();
    }
  };

  const handleOtpKeyDown = (index, e, isVerify = false) => {
    if (e.key === 'Backspace' && !e.target.value && index > 0) {
      const prevInput = document.getElementById(`${isVerify ? 'verify' : 'otp'}-${index - 1}`);
      if (prevInput) prevInput.focus();
    }
  };

  // Login handlers
  const handlePasswordLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await authService.loginPassword(loginData.email, loginData.password);
      if (result.success) {
        login(result.data.access_token);
        navigate('/owner/dashboard');
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
        navigate('/owner/dashboard');
      } else {
        setError(result.message || 'Invalid code');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  // Signup handlers
  const handleSignup = async (e) => {
    e.preventDefault();
    setError('');

    if (!signupData.firstName || !signupData.lastName || !signupData.email || !signupData.password) {
      setError('Please fill all required fields');
      return;
    }

    if (signupData.password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setLoading(true);

    try {
      const fullName = `${signupData.firstName} ${signupData.lastName}`;
      const result = await authService.signup(signupData.email, signupData.password, fullName);
      
      if (result.success) {
        setSignupPanel('verify');
      } else {
        setError(result.message || 'Signup failed');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Signup failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyEmail = async (e) => {
    e.preventDefault();
    const code = verifyCode.join('');
    if (code.length !== 6) {
      setError('Please enter all 6 digits');
      return;
    }
    setError('');
    setLoading(true);

    try {
      const result = await authService.verifyCode(signupData.email, code);
      
      if (result.success) {
        alert('Email verified successfully! Please login.');
        switchView('login');
      } else {
        setError(result.message || 'Verification failed');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  const handleResendCode = async (isSignup = false) => {
    setError('');
    setLoading(true);

    try {
      const email = isSignup ? signupData.email : loginData.email;
      const result = await authService.requestCode(email);
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
    <div className="ch-shell" data-view={activeView}>
      {/* Green Visual Panel - Swaps position */}
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
            <span className="ch-badge-text">{activeView === 'login' ? 'Live Bookings' : 'Join Today'}</span>
          </div>

          <h1 className="ch-hero-title">
            {activeView === 'login' ? (
              <>Play More,<br /><span className="accent">Book Smarter.</span></>
            ) : (
              <>Your Game,<br /><span className="accent">Your Court.</span></>
            )}
          </h1>

          <p className="ch-hero-subtitle">
            {activeView === 'login' 
              ? 'Discover and book premium indoor sports venues across your city in seconds'
              : 'List your sports facilities and reach thousands of players looking for their next game'
            }
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
            <span className="ch-cta-text">{activeView === 'login' ? 'New here?' : 'Have an account?'}</span>
            <button className="ch-cta-btn" onClick={() => switchView(activeView === 'login' ? 'signup' : 'login')}>
              {activeView === 'login' ? 'Create Account →' : '← Sign In'}
            </button>
          </div>
        </div>
      </div>

      {/* White Form Panel - Swaps position */}
      <div className="ch-form-panel">
        <div className="ch-emoji-watermark">
          {Array.from({ length: 42 }).map((_, i) => (
            <div key={i} className="ch-emoji-cell">
              {['🏏', '⚽', '🎾', '🏸', '🏀', '🏐'][i % 6]}
            </div>
          ))}
        </div>

        <div className="ch-form-content">
          {activeView === 'login' ? (
            // LOGIN FORMS
            <div className="ch-form-viewport">
              {/* Main Login Panel */}
              <div className={`ch-form-inner ${loginPanel === 'main' ? 'active' : 'exiting'}`}>
                <h2 className="ch-form-title">Welcome back</h2>
                <p className="ch-form-subtitle">Sign in to manage your sports venues</p>

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
                  New to CourtHub? <button onClick={() => switchView('signup')}>Create account</button>
                </p>
              </div>

              {/* OTP Login Panel */}
              <div className={`ch-form-inner ${loginPanel === 'otp' ? 'active' : ''}`}>
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
                  Didn't receive code? <button onClick={() => handleResendCode(false)}>Resend</button>
                </p>
              </div>
            </div>
          ) : (
            // SIGNUP FORMS
            <div className="ch-form-viewport">
              {/* Signup Form Panel */}
              <div className={`ch-form-inner ${signupPanel === 'form' ? 'active' : 'exiting'}`}>
                <div className="ch-step-dots">
                  <div className="ch-dot active"></div>
                  <div className="ch-dot"></div>
                </div>

                <h2 className="ch-form-title">Create Account</h2>
                <p className="ch-form-subtitle">Join CourtHub and start managing your venues</p>

                {error && <div className="ch-error-box">{error}</div>}

                <form onSubmit={handleSignup}>
                  <div className="ch-field-row">
                    <div className="ch-field">
                      <label>FIRST NAME</label>
                      <input
                        type="text"
                        value={signupData.firstName}
                        onChange={(e) => setSignupData({ ...signupData, firstName: e.target.value })}
                        placeholder="John"
                        required
                      />
                    </div>
                    <div className="ch-field">
                      <label>LAST NAME</label>
                      <input
                        type="text"
                        value={signupData.lastName}
                        onChange={(e) => setSignupData({ ...signupData, lastName: e.target.value })}
                        placeholder="Doe"
                        required
                      />
                    </div>
                  </div>

                  <div className="ch-field">
                    <label>EMAIL</label>
                    <input
                      type="email"
                      value={signupData.email}
                      onChange={(e) => setSignupData({ ...signupData, email: e.target.value })}
                      placeholder="your@email.com"
                      required
                    />
                  </div>

                  <div className="ch-field">
                    <label>PHONE (OPTIONAL)</label>
                    <input
                      type="tel"
                      value={signupData.phone}
                      onChange={(e) => setSignupData({ ...signupData, phone: e.target.value })}
                      placeholder="+1 234 567 8900"
                    />
                  </div>

                  <div className="ch-field">
                    <label>PASSWORD</label>
                    <input
                      type="password"
                      value={signupData.password}
                      onChange={(e) => setSignupData({ ...signupData, password: e.target.value })}
                      placeholder="Min. 6 characters"
                      required
                      minLength="6"
                    />
                  </div>

                  <button type="submit" className="ch-btn-primary" disabled={loading}>
                    {loading ? 'Creating...' : 'Continue →'}
                  </button>
                </form>

                <p className="ch-bottom-note">
                  Already have an account? <button onClick={() => switchView('login')}>Sign in</button>
                </p>
              </div>

              {/* Verify Email Panel */}
              <div className={`ch-form-inner ${signupPanel === 'verify' ? 'active' : ''}`}>
                <div className="ch-step-dots">
                  <div className="ch-dot"></div>
                  <div className="ch-dot active"></div>
                </div>

                <div className="ch-icon-box">✉️</div>
                <h2 className="ch-form-title">Verify Email</h2>
                <p className="ch-form-subtitle">Enter the 6-digit code sent to {signupData.email}</p>

                {error && <div className="ch-error-box">{error}</div>}

                <form onSubmit={handleVerifyEmail}>
                  <div className="ch-otp-row">
                    {verifyCode.map((digit, index) => (
                      <input
                        key={index}
                        id={`verify-${index}`}
                        type="text"
                        maxLength="1"
                        value={digit}
                        onChange={(e) => handleOtpChange(index, e.target.value, true)}
                        onKeyDown={(e) => handleOtpKeyDown(index, e, true)}
                        className="ch-otp-box"
                      />
                    ))}
                  </div>

                  <button type="submit" className="ch-btn-primary" disabled={loading}>
                    {loading ? 'Verifying...' : 'Verify & Finish →'}
                  </button>
                </form>

                <button className="ch-btn-outline" onClick={() => setSignupPanel('form')}>
                  ← Go Back
                </button>

                <p className="ch-resend-note">
                  Didn't receive code? <button onClick={() => handleResendCode(true)}>Resend</button>
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Auth;

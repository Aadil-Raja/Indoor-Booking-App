import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../../services/authService';
import './auth.css';

const Signup = () => {
  const [signupPanel, setSignupPanel] = useState('form');
  const [signupData, setSignupData] = useState({ 
    firstName: '', 
    lastName: '', 
    email: '', 
    phone: '', 
    password: '' 
  });
  const [verifyCode, setVerifyCode] = useState(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const navigate = useNavigate();

  const handleOtpChange = (index, value) => {
    if (value.length > 1) value = value[0];
    if (!/^\d*$/.test(value)) return;

    const newOtp = [...verifyCode];
    newOtp[index] = value;
    setVerifyCode(newOtp);

    if (value && index < 5) {
      const nextInput = document.getElementById(`verify-${index + 1}`);
      if (nextInput) nextInput.focus();
    }
  };

  const handleOtpKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !e.target.value && index > 0) {
      const prevInput = document.getElementById(`verify-${index - 1}`);
      if (prevInput) prevInput.focus();
    }
  };

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
      const result = await authService.signup(signupData.email, signupData.password, fullName, 'owner');
      
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
        navigate('/login');
      } else {
        setError(result.message || 'Verification failed');
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
      const result = await authService.requestCode(signupData.email);
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
    <div className="ch-shell" data-view="signup">
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
            <span className="ch-badge-text">Owner Portal</span>
          </div>

          <h1 className="ch-hero-title">
            List Your<br /><span className="accent">Venues Today.</span>
          </h1>

          <p className="ch-hero-subtitle">
            Join CourtHub and start managing your sports facilities
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
            <span className="ch-cta-text">Have an account?</span>
            <button className="ch-cta-btn" onClick={() => navigate('/login')}>
              ← Sign In
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
            {signupPanel === 'form' ? (
              <div className="ch-form-inner active">
                <div className="ch-step-dots">
                  <div className="ch-dot active"></div>
                  <div className="ch-dot"></div>
                </div>

                <h2 className="ch-form-title">Create Owner Account</h2>
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
                  Already have an account? <button onClick={() => navigate('/login')}>Sign in</button>
                </p>
              </div>
            ) : (
              <div className="ch-form-inner active">
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
                        onChange={(e) => handleOtpChange(index, e.target.value)}
                        onKeyDown={(e) => handleOtpKeyDown(index, e)}
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

export default Signup;

import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ownerService } from '../../services/ownerService';
import './ownerProfile.css';

const OwnerProfile = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [profile, setProfile] = useState({
    business_name: '',
    phone: '',
    address: ''
  });
  const [originalProfile, setOriginalProfile] = useState(null);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      setLoading(true);
      setError('');
      const result = await ownerService.getProfile();

      if (result.success && result.data) {
        const profileData = {
          business_name: result.data.business_name || '',
          phone: result.data.phone || '',
          address: result.data.address || ''
        };
        setProfile(profileData);
        setOriginalProfile(profileData);
      } else {
        // Profile doesn't exist yet, keep empty form
        setOriginalProfile(profile);
      }
    } catch (err) {
      if (err.response?.status === 404) {
        // Profile not found, user can create one
        setOriginalProfile(profile);
      } else {
        setError(err.response?.data?.message || 'Failed to load profile');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setProfile(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear messages when user starts typing
    setError('');
    setSuccess('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setSaving(true);

    try {
      const result = await ownerService.updateProfile(profile);

      if (result.success) {
        setSuccess('Profile updated successfully!');
        setOriginalProfile(profile);
        // Clear success message after 3 seconds
        setTimeout(() => setSuccess(''), 3000);
      } else {
        setError(result.message || 'Failed to update profile');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setProfile(originalProfile);
    setError('');
    setSuccess('');
  };

  const hasChanges = JSON.stringify(profile) !== JSON.stringify(originalProfile);

  if (loading) {
    return (
      <div className="ib-profile-container">
        <header className="ib-profile-header">
          <h1>Owner Profile</h1>
          <Link to="/owner/dashboard" className="ib-profile-btn-back">
            Back to Dashboard
          </Link>
        </header>
        <div className="ib-profile-content">
          <div className="ib-profile-loading">Loading profile...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="ib-profile-container">
      <header className="ib-profile-header">
        <h1>Owner Profile</h1>
        <Link to="/owner/dashboard" className="ib-profile-btn-back">
          Back to Dashboard
        </Link>
      </header>

      <div className="ib-profile-content">
        <div className="ib-profile-card">
          <div className="ib-profile-card-header">
            <h2>Business Information</h2>
            <span className="ib-profile-verification-badge unverified">
              ⚠ Unverified
            </span>
          </div>

          {error && <div className="ib-profile-error-message">{error}</div>}
          {success && <div className="ib-profile-success-message">{success}</div>}

          <form onSubmit={handleSubmit}>
            <div className="ib-profile-form-group">
              <label htmlFor="business_name">Business Name</label>
              <input
                type="text"
                id="business_name"
                name="business_name"
                value={profile.business_name}
                onChange={handleChange}
                placeholder="Enter your business name"
              />
            </div>

            <div className="ib-profile-form-group">
              <label htmlFor="phone">Phone Number</label>
              <input
                type="tel"
                id="phone"
                name="phone"
                value={profile.phone}
                onChange={handleChange}
                placeholder="Enter your phone number"
              />
            </div>

            <div className="ib-profile-form-group">
              <label htmlFor="address">Business Address</label>
              <textarea
                id="address"
                name="address"
                value={profile.address}
                onChange={handleChange}
                placeholder="Enter your business address"
              />
            </div>

            <div className="ib-profile-form-actions">
              <button
                type="button"
                className="ib-profile-btn-secondary"
                onClick={handleCancel}
                disabled={!hasChanges || saving}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="ib-profile-btn-primary"
                disabled={!hasChanges || saving}
              >
                {saving ? 'Saving...' : 'Save Profile'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default OwnerProfile;

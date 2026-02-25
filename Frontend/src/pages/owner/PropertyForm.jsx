import { useState, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { propertyService } from '../../services/propertyService';
import './property.css';

const PropertyForm = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEditMode = !!id;

  const [loading, setLoading] = useState(isEditMode);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    address: '',
    city: '',
    state: '',
    country: 'Pakistan',
    maps_link: '',
    phone: '',
    email: '',
    amenities: []
  });
  const [newAmenity, setNewAmenity] = useState('');

  useEffect(() => {
    if (isEditMode) {
      fetchProperty();
    }
  }, [id]);

  const fetchProperty = async () => {
    try {
      setLoading(true);
      setError('');
      const result = await propertyService.getPropertyDetails(id);

      if (result.success && result.data) {
        setFormData({
          name: result.data.name || '',
          description: result.data.description || '',
          address: result.data.address || '',
          city: result.data.city || '',
          state: result.data.state || '',
          country: result.data.country || 'Pakistan',
          maps_link: result.data.maps_link || '',
          phone: result.data.phone || '',
          email: result.data.email || '',
          amenities: result.data.amenities || []
        });
      } else {
        setError('Property not found');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load property');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value
    }));
    setError('');
  };

  const handleAddAmenity = () => {
    if (newAmenity.trim() && !formData.amenities.includes(newAmenity.trim())) {
      setFormData((prev) => ({
        ...prev,
        amenities: [...prev.amenities, newAmenity.trim()]
      }));
      setNewAmenity('');
    }
  };

  const handleRemoveAmenity = (amenity) => {
    setFormData((prev) => ({
      ...prev,
      amenities: prev.amenities.filter((a) => a !== amenity)
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSaving(true);

    // Validation
    if (!formData.name.trim()) {
      setError('Property name is required');
      setSaving(false);
      return;
    }

    if (!formData.address.trim()) {
      setError('Address is required');
      setSaving(false);
      return;
    }

    try {
      // Prepare data - remove empty strings and ensure proper types
      const dataToSend = {
        name: formData.name.trim(),
        address: formData.address.trim(),
        country: formData.country.trim() || 'Pakistan',
        amenities: formData.amenities || []
      };

      // Only include optional fields if they have values
      if (formData.description?.trim()) {
        dataToSend.description = formData.description.trim();
      }
      if (formData.city?.trim()) {
        dataToSend.city = formData.city.trim();
      }
      if (formData.state?.trim()) {
        dataToSend.state = formData.state.trim();
      }
      if (formData.maps_link?.trim()) {
        dataToSend.maps_link = formData.maps_link.trim();
      }
      if (formData.phone?.trim()) {
        dataToSend.phone = formData.phone.trim();
      }
      if (formData.email?.trim()) {
        dataToSend.email = formData.email.trim();
      }

      const result = isEditMode
        ? await propertyService.updateProperty(id, dataToSend)
        : await propertyService.createProperty(dataToSend);

      if (result.success) {
        navigate('/owner/properties');
      } else {
        setError(result.message || 'Failed to save property');
      }
    } catch (err) {
      console.error('Error saving property:', err);
      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          'Failed to save property'
      );
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="ib-property-container">
        <header className="ib-property-header">
          <h1>{isEditMode ? 'Edit Property' : 'Add New Property'}</h1>
          <Link to="/owner/properties" className="ib-property-btn-back">
            Back to Properties
          </Link>
        </header>
        <div className="ib-property-content">
          <div className="ib-property-loading">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="ib-property-container">
      <header className="ib-property-header">
        <h1>{isEditMode ? 'Edit Property' : 'Add New Property'}</h1>
        <Link to="/owner/properties" className="ib-property-btn-back">
          Back to Properties
        </Link>
      </header>

      <div className="ib-property-content">
        <div className="ib-property-form-card">
          {error && <div className="ib-property-error-message">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="ib-property-form-group">
              <label htmlFor="name">
                Property Name <span style={{ color: 'red' }}>*</span>
              </label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="e.g., Sports Arena Complex"
                required
              />
            </div>

            <div className="ib-property-form-group">
              <label htmlFor="description">Description</label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                placeholder="Describe your property..."
              />
            </div>

            <div className="ib-property-form-group">
              <label htmlFor="address">
                Address <span style={{ color: 'red' }}>*</span>
              </label>
              <textarea
                id="address"
                name="address"
                value={formData.address}
                onChange={handleChange}
                placeholder="Enter full address"
                required
              />
            </div>

            <div className="ib-property-form-row">
              <div className="ib-property-form-group">
                <label htmlFor="city">City</label>
                <input
                  type="text"
                  id="city"
                  name="city"
                  value={formData.city}
                  onChange={handleChange}
                  placeholder="e.g., Karachi"
                />
              </div>

              <div className="ib-property-form-group">
                <label htmlFor="state">State/Province</label>
                <input
                  type="text"
                  id="state"
                  name="state"
                  value={formData.state}
                  onChange={handleChange}
                  placeholder="e.g., Sindh"
                />
              </div>
            </div>

            <div className="ib-property-form-row">
              <div className="ib-property-form-group">
                <label htmlFor="country">Country</label>
                <input
                  type="text"
                  id="country"
                  name="country"
                  value={formData.country}
                  onChange={handleChange}
                  placeholder="Pakistan"
                />
              </div>

              <div className="ib-property-form-group">
                <label htmlFor="maps_link">Google Maps Link</label>
                <input
                  type="url"
                  id="maps_link"
                  name="maps_link"
                  value={formData.maps_link}
                  onChange={handleChange}
                  placeholder="https://maps.google.com/..."
                />
              </div>
            </div>

            <div className="ib-property-form-row">
              <div className="ib-property-form-group">
                <label htmlFor="phone">Phone Number</label>
                <input
                  type="tel"
                  id="phone"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  placeholder="+92 300 1234567"
                />
              </div>

              <div className="ib-property-form-group">
                <label htmlFor="email">Email</label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="property@example.com"
                />
              </div>
            </div>

            <div className="ib-property-form-group">
              <label htmlFor="amenities">Amenities</label>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                <input
                  type="text"
                  id="amenities"
                  value={newAmenity}
                  onChange={(e) => setNewAmenity(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddAmenity();
                    }
                  }}
                  placeholder="e.g., Parking, WiFi, Locker Room"
                />
                <button
                  type="button"
                  onClick={handleAddAmenity}
                  className="ib-property-btn-primary"
                  style={{ flex: '0 0 auto', padding: '12px 24px' }}
                >
                  Add
                </button>
              </div>
              {formData.amenities.length > 0 && (
                <div className="ib-property-amenities">
                  {formData.amenities.map((amenity, index) => (
                    <span key={index} className="ib-property-amenity-tag">
                      {amenity}
                      <button
                        type="button"
                        onClick={() => handleRemoveAmenity(amenity)}
                        className="ib-property-amenity-remove"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="ib-property-form-actions">
              <Link
                to="/owner/properties"
                className="ib-property-btn-secondary"
              >
                Cancel
              </Link>
              <button
                type="submit"
                className="ib-property-btn-primary"
                disabled={saving}
              >
                {saving
                  ? 'Saving...'
                  : isEditMode
                  ? 'Update Property'
                  : 'Create Property'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default PropertyForm;

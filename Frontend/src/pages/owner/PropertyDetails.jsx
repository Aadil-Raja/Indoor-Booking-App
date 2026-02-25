import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { propertyService } from '../../services/propertyService';
import './property.css';

const PropertyDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [property, setProperty] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchProperty();
  }, [id]);

  const fetchProperty = async () => {
    try {
      setLoading(true);
      setError('');
      const result = await propertyService.getPropertyDetails(id);

      if (result.success && result.data) {
        setProperty(result.data);
      } else {
        setError('Property not found');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load property');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (
      !window.confirm(
        `Are you sure you want to delete "${property.name}"? This will also delete all courts associated with this property.`
      )
    ) {
      return;
    }

    try {
      const result = await propertyService.deleteProperty(id);

      if (result.success) {
        navigate('/owner/properties');
      } else {
        alert(result.message || 'Failed to delete property');
      }
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to delete property');
    }
  };

  if (loading) {
    return (
      <div className="ib-property-container">
        <header className="ib-property-header">
          <h1>Property Details</h1>
          <Link to="/owner/properties" className="ib-property-btn-back">
            Back to Properties
          </Link>
        </header>
        <div className="ib-property-content">
          <div className="ib-property-loading">Loading property...</div>
        </div>
      </div>
    );
  }

  if (error || !property) {
    return (
      <div className="ib-property-container">
        <header className="ib-property-header">
          <h1>Property Details</h1>
          <Link to="/owner/properties" className="ib-property-btn-back">
            Back to Properties
          </Link>
        </header>
        <div className="ib-property-content">
          <div className="ib-property-error-message">
            {error || 'Property not found'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="ib-property-container">
      <header className="ib-property-header">
        <h1>{property.name}</h1>
        <div className="ib-property-header-actions">
          <Link to="/owner/properties" className="ib-property-btn-back">
            Back to Properties
          </Link>
          <Link
            to={`/owner/properties/${id}/edit`}
            className="ib-property-btn-add"
          >
            Edit Property
          </Link>
        </div>
      </header>

      <div className="ib-property-content">
        <div className="ib-property-details-grid">
          {/* Property Information */}
          <div className="ib-property-info-card">
            <h2>Property Information</h2>

            <div className="ib-property-info-row">
              <div className="ib-property-info-label">Status</div>
              <div className="ib-property-info-value">
                <span
                  className={`ib-property-status-badge ${
                    property.is_active ? 'active' : 'inactive'
                  }`}
                >
                  {property.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>

            {property.description && (
              <div className="ib-property-info-row">
                <div className="ib-property-info-label">Description</div>
                <div className="ib-property-info-value">
                  {property.description}
                </div>
              </div>
            )}

            <div className="ib-property-info-row">
              <div className="ib-property-info-label">Address</div>
              <div className="ib-property-info-value">{property.address}</div>
            </div>

            {property.city && (
              <div className="ib-property-info-row">
                <div className="ib-property-info-label">City</div>
                <div className="ib-property-info-value">{property.city}</div>
              </div>
            )}

            {property.state && (
              <div className="ib-property-info-row">
                <div className="ib-property-info-label">State/Province</div>
                <div className="ib-property-info-value">{property.state}</div>
              </div>
            )}

            <div className="ib-property-info-row">
              <div className="ib-property-info-label">Country</div>
              <div className="ib-property-info-value">{property.country}</div>
            </div>

            {property.maps_link && (
              <div className="ib-property-info-row">
                <div className="ib-property-info-label">Maps Link</div>
                <div className="ib-property-info-value">
                  <a
                    href={property.maps_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: 'var(--color-primary)' }}
                  >
                    View on Google Maps
                  </a>
                </div>
              </div>
            )}

            {property.phone && (
              <div className="ib-property-info-row">
                <div className="ib-property-info-label">Phone</div>
                <div className="ib-property-info-value">{property.phone}</div>
              </div>
            )}

            {property.email && (
              <div className="ib-property-info-row">
                <div className="ib-property-info-label">Email</div>
                <div className="ib-property-info-value">{property.email}</div>
              </div>
            )}

            {property.amenities && property.amenities.length > 0 && (
              <div className="ib-property-info-row">
                <div className="ib-property-info-label">Amenities</div>
                <div className="ib-property-info-value">
                  <div className="ib-property-amenities">
                    {property.amenities.map((amenity, index) => (
                      <span key={index} className="ib-property-amenity-tag">
                        {amenity}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Courts Section */}
          <div className="ib-property-info-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)' }}>
              <h2 style={{ margin: 0, paddingBottom: 0, border: 'none' }}>Courts</h2>
              <Link
                to={`/owner/properties/${id}/courts/new`}
                className="ib-property-btn-view"
                style={{ padding: '8px 16px', fontSize: '14px' }}
              >
                + Add Court
              </Link>
            </div>
            {property.courts && property.courts.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
                {property.courts.map((court) => (
                  <div
                    key={court.id}
                    style={{
                      padding: 'var(--spacing-md)',
                      background: 'var(--color-gray-50)',
                      borderRadius: 'var(--radius-md)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, marginBottom: '4px' }}>
                        {court.name}
                      </div>
                      <div style={{ fontSize: '14px', color: 'var(--color-gray-600)' }}>
                        {court.sport_type}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <Link
                        to={`/owner/courts/${court.id}/edit`}
                        className="ib-property-btn-edit"
                        style={{ padding: '6px 12px', fontSize: '13px' }}
                      >
                        Edit
                      </Link>
                      <span
                        className={`ib-property-status-badge ${
                          court.is_active ? 'active' : 'inactive'
                        }`}
                      >
                        {court.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="ib-property-empty-state">
                <p>No courts added yet</p>
                <Link
                  to={`/owner/properties/${id}/courts/new`}
                  className="ib-property-btn-primary"
                  style={{ display: 'inline-block', marginTop: '1rem', padding: '12px 24px' }}
                >
                  + Add First Court
                </Link>
              </div>
            )}
          </div>

          {/* Danger Zone */}
          <div className="ib-property-info-card">
            <h2 style={{ color: 'var(--color-error)' }}>Danger Zone</h2>
            <div className="ib-property-info-row">
              <div className="ib-property-info-label">Delete Property</div>
              <div className="ib-property-info-value">
                <button
                  onClick={handleDelete}
                  className="ib-property-btn-delete"
                  style={{ width: 'auto' }}
                >
                  Delete This Property
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PropertyDetails;

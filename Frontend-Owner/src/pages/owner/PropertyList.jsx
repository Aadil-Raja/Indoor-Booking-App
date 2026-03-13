import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { propertyService } from '../../services/propertyService';
import OwnerLayout from '../../components/Layout/OwnerLayout';
import './property.css';

const PropertyList = () => {
  const navigate = useNavigate();
  const [properties, setProperties] = useState([]);
  const [filteredProperties, setFilteredProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchProperties();
  }, []);

  useEffect(() => {
    if (searchTerm) {
      const filtered = properties.filter(
        (property) =>
          property.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          property.city?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          property.state?.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredProperties(filtered);
    } else {
      setFilteredProperties(properties);
    }
  }, [searchTerm, properties]);

  const fetchProperties = async () => {
    try {
      setLoading(true);
      setError('');
      const result = await propertyService.getProperties();

      if (result.success) {
        setProperties(result.data || []);
      } else {
        setError(result.message || 'Failed to load properties');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load properties');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (propertyId, propertyName) => {
    if (
      !window.confirm(
        `Are you sure you want to delete "${propertyName}"? This will also delete all courts associated with this property.`
      )
    ) {
      return;
    }

    try {
      const result = await propertyService.deleteProperty(propertyId);

      if (result.success) {
        setProperties(properties.filter((p) => p.id !== propertyId));
      } else {
        alert(result.message || 'Failed to delete property');
      }
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to delete property');
    }
  };

  if (loading) {
    return (
      <OwnerLayout>
        <div className="ib-page-container">
          <div className="ib-page-header">
            <h1>My Properties</h1>
          </div>
          <div className="ib-page-content">
            <div className="ib-property-loading">Loading properties...</div>
          </div>
        </div>
      </OwnerLayout>
    );
  }

  return (
    <OwnerLayout>
      <div className="ib-page-container">
        <div className="ib-page-header">
          <h1>My Properties</h1>
          <Link to="/properties/new" className="ib-btn-primary">
            + Add Property
          </Link>
        </div>

        <div className="ib-page-content">
        {error && <div className="ib-property-error-message">{error}</div>}

        {properties.length > 0 && (
          <div className="ib-property-search">
            <input
              type="text"
              placeholder="Search properties by name, city, or state..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        )}

        {filteredProperties.length === 0 ? (
          <div className="ib-property-empty-state">
            <h2>No Properties Found</h2>
            <p>
              {searchTerm
                ? 'No properties match your search.'
                : 'Get started by adding your first property.'}
            </p>
            {!searchTerm && (
              <Link
                to="/properties/new"
                className="ib-property-btn-primary"
                style={{ display: 'inline-block', marginTop: '1rem' }}
              >
                + Add Your First Property
              </Link>
            )}
          </div>
        ) : (
          <div className="ib-property-grid">
            {filteredProperties.map((property) => (
              <div key={property.id} className="ib-property-card">
                <div className="ib-property-card-header">
                  <div className="ib-property-card-title">
                    <h3>{property.name}</h3>
                    <div className="ib-property-card-location">
                      📍{' '}
                      {[property.city, property.state]
                        .filter(Boolean)
                        .join(', ') || 'Location not specified'}
                    </div>
                  </div>
                  <span
                    className={`ib-property-status-badge ${
                      property.is_active ? 'active' : 'inactive'
                    }`}
                  >
                    {property.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>

                <div className="ib-property-card-actions">
                  <Link
                    to={`/properties/${property.id}`}
                    className="ib-property-btn-view"
                  >
                    View
                  </Link>
                  <Link
                    to={`/properties/${property.id}/edit`}
                    className="ib-property-btn-edit"
                  >
                    Edit
                  </Link>
                  <button
                    onClick={() => handleDelete(property.id, property.name)}
                    className="ib-property-btn-delete"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        </div>
      </div>
    </OwnerLayout>
  );
};

export default PropertyList;

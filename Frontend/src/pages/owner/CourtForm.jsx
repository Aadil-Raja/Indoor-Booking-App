import { useState, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { courtService } from '../../services/courtService';
import './court.css';

const CourtForm = () => {
  const navigate = useNavigate();
  const { propertyId, id } = useParams();
  const isEditMode = !!id;

  const [loading, setLoading] = useState(isEditMode);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    sport_type: '',
    description: '',
    specifications: {},
    amenities: []
  });
  const [newAmenity, setNewAmenity] = useState('');
  const [newSpecKey, setNewSpecKey] = useState('');
  const [newSpecValue, setNewSpecValue] = useState('');

  useEffect(() => {
    if (isEditMode) {
      fetchCourt();
    }
  }, [id]);

  const fetchCourt = async () => {
    try {
      setLoading(true);
      setError('');
      const result = await courtService.getCourtDetails(id);

      if (result.success && result.data) {
        setFormData({
          name: result.data.name || '',
          sport_type: result.data.sport_type || '',
          description: result.data.description || '',
          specifications: result.data.specifications || {},
          amenities: result.data.amenities || []
        });
      } else {
        setError('Court not found');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load court');
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

  const handleAddSpecification = () => {
    if (newSpecKey.trim() && newSpecValue.trim()) {
      setFormData((prev) => ({
        ...prev,
        specifications: {
          ...prev.specifications,
          [newSpecKey.trim()]: newSpecValue.trim()
        }
      }));
      setNewSpecKey('');
      setNewSpecValue('');
    }
  };

  const handleRemoveSpecification = (key) => {
    setFormData((prev) => {
      const newSpecs = { ...prev.specifications };
      delete newSpecs[key];
      return {
        ...prev,
        specifications: newSpecs
      };
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSaving(true);

    // Validation
    if (!formData.name.trim()) {
      setError('Court name is required');
      setSaving(false);
      return;
    }

    if (!formData.sport_type.trim()) {
      setError('Sport type is required');
      setSaving(false);
      return;
    }

    try {
      // Prepare data
      const dataToSend = {
        name: formData.name.trim(),
        sport_type: formData.sport_type.trim(),
        specifications: formData.specifications || {},
        amenities: formData.amenities || []
      };

      if (formData.description?.trim()) {
        dataToSend.description = formData.description.trim();
      }

      const result = isEditMode
        ? await courtService.updateCourt(id, dataToSend)
        : await courtService.createCourt(propertyId, dataToSend);

      if (result.success) {
        navigate(`/owner/properties/${propertyId || result.data.property_id}`);
      } else {
        setError(result.message || 'Failed to save court');
      }
    } catch (err) {
      console.error('Error saving court:', err);
      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          'Failed to save court'
      );
    } finally {
      setSaving(false);
    }
  };

  const backUrl = propertyId
    ? `/owner/properties/${propertyId}`
    : '/owner/properties';

  if (loading) {
    return (
      <div className="ib-court-container">
        <header className="ib-court-header">
          <h1>{isEditMode ? 'Edit Court' : 'Add New Court'}</h1>
          <Link to={backUrl} className="ib-court-btn-back">
            Back
          </Link>
        </header>
        <div className="ib-court-content">
          <div className="ib-court-loading">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="ib-court-container">
      <header className="ib-court-header">
        <h1>{isEditMode ? 'Edit Court' : 'Add New Court'}</h1>
        <Link to={backUrl} className="ib-court-btn-back">
          Back
        </Link>
      </header>

      <div className="ib-court-content">
        <div className="ib-court-form-card">
          {error && <div className="ib-court-error-message">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="ib-court-form-row">
              <div className="ib-court-form-group">
                <label htmlFor="name">
                  Court Name <span style={{ color: 'red' }}>*</span>
                </label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="e.g., Court 1, Main Arena"
                  required
                />
              </div>

              <div className="ib-court-form-group">
                <label htmlFor="sport_type">
                  Sport Type <span style={{ color: 'red' }}>*</span>
                </label>
                <input
                  type="text"
                  id="sport_type"
                  name="sport_type"
                  value={formData.sport_type}
                  onChange={handleChange}
                  placeholder="e.g., Badminton, Tennis, Football"
                  required
                />
              </div>
            </div>

            <div className="ib-court-form-group">
              <label htmlFor="description">Description</label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                placeholder="Describe the court..."
              />
            </div>

            <div className="ib-court-form-group">
              <label>Specifications</label>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                <input
                  type="text"
                  value={newSpecKey}
                  onChange={(e) => setNewSpecKey(e.target.value)}
                  placeholder="Key (e.g., Surface Type)"
                  style={{ flex: 1 }}
                />
                <input
                  type="text"
                  value={newSpecValue}
                  onChange={(e) => setNewSpecValue(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddSpecification();
                    }
                  }}
                  placeholder="Value (e.g., Synthetic)"
                  style={{ flex: 1 }}
                />
                <button
                  type="button"
                  onClick={handleAddSpecification}
                  className="ib-court-btn-add-spec"
                >
                  Add
                </button>
              </div>
              {Object.keys(formData.specifications).length > 0 && (
                <div className="ib-court-spec-list">
                  {Object.entries(formData.specifications).map(([key, value]) => (
                    <div key={key} className="ib-court-spec-item">
                      <input type="text" value={`${key}: ${value}`} disabled />
                      <button
                        type="button"
                        onClick={() => handleRemoveSpecification(key)}
                        className="ib-court-spec-remove"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="ib-court-form-group">
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
                  placeholder="e.g., Lighting, Seating, Scoreboard"
                />
                <button
                  type="button"
                  onClick={handleAddAmenity}
                  className="ib-court-btn-primary"
                  style={{ flex: '0 0 auto', padding: '12px 24px' }}
                >
                  Add
                </button>
              </div>
              {formData.amenities.length > 0 && (
                <div className="ib-court-amenities">
                  {formData.amenities.map((amenity, index) => (
                    <span key={index} className="ib-court-amenity-tag">
                      {amenity}
                      <button
                        type="button"
                        onClick={() => handleRemoveAmenity(amenity)}
                        className="ib-court-amenity-remove"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="ib-court-form-actions">
              <Link to={backUrl} className="ib-court-btn-secondary">
                Cancel
              </Link>
              <button
                type="submit"
                className="ib-court-btn-primary"
                disabled={saving}
              >
                {saving
                  ? 'Saving...'
                  : isEditMode
                  ? 'Update Court'
                  : 'Create Court'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default CourtForm;

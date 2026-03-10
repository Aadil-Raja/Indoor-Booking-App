import { useState, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { courtService } from '../../services/courtService';
import OwnerLayout from '../../components/Layout/OwnerLayout';
import './court.css';

const CourtForm = () => {
  const navigate = useNavigate();
  const { propertyId, id } = useParams();
  const isEditMode = !!id;

  const [loading, setLoading] = useState(isEditMode);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [sportTypes, setSportTypes] = useState([]);
  const [loadingSportTypes, setLoadingSportTypes] = useState(true);
  const [formData, setFormData] = useState({
    name: '',
    sport_types: [],
    description: '',
    specifications: {},
    amenities: []
  });
  const [newAmenity, setNewAmenity] = useState('');
  const [newSpecKey, setNewSpecKey] = useState('');
  const [newSpecValue, setNewSpecValue] = useState('');

  useEffect(() => {
    fetchSportTypes();
  }, []);

  useEffect(() => {
    if (isEditMode) {
      fetchCourt();
    }
  }, [id]);

  const fetchSportTypes = async () => {
    try {
      setLoadingSportTypes(true);
      const result = await courtService.getSportTypes();
      if (result.success && result.data) {
        setSportTypes(result.data);
      }
    } catch (err) {
      console.error('Failed to load sport types:', err);
      // Fallback to hardcoded values if API fails
      setSportTypes([
        { value: 'futsal', label: 'Futsal' },
        { value: 'football', label: 'Football' },
        { value: 'cricket', label: 'Cricket' },
        { value: 'hockey', label: 'Hockey' },
        { value: 'padel', label: 'Padel' },
        { value: 'badminton', label: 'Badminton' },
        { value: 'tennis', label: 'Tennis' }
      ]);
    } finally {
      setLoadingSportTypes(false);
    }
  };

  const fetchCourt = async () => {
    try {
      setLoading(true);
      setError('');
      const result = await courtService.getCourtDetails(id);

      if (result.success && result.data) {
        setFormData({
          name: result.data.name || '',
          sport_types: result.data.sport_types || [],
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

  const handleSportTypeToggle = (sportValue) => {
    setFormData((prev) => {
      const isSelected = prev.sport_types.includes(sportValue);
      return {
        ...prev,
        sport_types: isSelected
          ? prev.sport_types.filter((s) => s !== sportValue)
          : [...prev.sport_types, sportValue]
      };
    });
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

    if (!formData.sport_types || formData.sport_types.length === 0) {
      setError('At least one sport type is required');
      setSaving(false);
      return;
    }

    try {
      // Prepare data
      const dataToSend = {
        name: formData.name.trim(),
        sport_types: formData.sport_types,
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
        // Navigate back to property details
        const targetPropertyId = propertyId || result.data?.property_id;
        if (targetPropertyId) {
          navigate(`/properties/${targetPropertyId}`);
        } else {
          navigate('/properties');
        }
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
    ? `/properties/${propertyId}`
    : '/properties';

  if (loading) {
    return (
      <OwnerLayout>
        <div className="ib-page-container">
          <div className="ib-page-header">
            <h1>{isEditMode ? 'Edit Court' : 'Add New Court'}</h1>
            <Link to={backUrl} className="ib-btn-secondary">
              Cancel
            </Link>
          </div>
          <div className="ib-page-content">
            <div className="ib-court-loading">Loading...</div>
          </div>
        </div>
      </OwnerLayout>
    );
  }

  return (
    <OwnerLayout>
      <div className="ib-page-container">
        <div className="ib-page-header">
          <h1>{isEditMode ? 'Edit Court' : 'Add New Court'}</h1>
          <Link to={backUrl} className="ib-btn-secondary">
            Cancel
          </Link>
        </div>

        <div className="ib-page-content">
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
            </div>

            <div className="ib-court-form-group">
              <label>
                Sport Types <span style={{ color: 'red' }}>*</span>
              </label>
              {loadingSportTypes ? (
                <div style={{ padding: '12px', color: '#666' }}>Loading sport types...</div>
              ) : (
                <>
                  <div className="ib-sport-types-grid">
                    {sportTypes.map((sport) => (
                      <div
                        key={sport.value}
                        className={`ib-sport-type-option ${
                          formData.sport_types.includes(sport.value) ? 'selected' : ''
                        }`}
                        onClick={() => handleSportTypeToggle(sport.value)}
                      >
                        <div className="ib-sport-type-checkbox">
                          {formData.sport_types.includes(sport.value) && (
                            <svg
                              width="16"
                              height="16"
                              viewBox="0 0 16 16"
                              fill="none"
                              xmlns="http://www.w3.org/2000/svg"
                            >
                              <path
                                d="M13.3334 4L6.00002 11.3333L2.66669 8"
                                stroke="currentColor"
                                strokeWidth="2"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                              />
                            </svg>
                          )}
                        </div>
                        <span className="ib-sport-type-label">{sport.label}</span>
                      </div>
                    ))}
                  </div>
                  {formData.sport_types.length > 0 && (
                    <div className="ib-selected-sports">
                      Selected: {formData.sport_types.map(st => 
                        sportTypes.find(s => s.value === st)?.label
                      ).join(', ')}
                    </div>
                  )}
                </>
              )}
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
                  onKeyDown={(e) => {
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
                  onKeyDown={(e) => {
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
    </OwnerLayout>
  );
};

export default CourtForm;

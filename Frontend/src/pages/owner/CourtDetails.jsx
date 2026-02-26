import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { courtService } from '../../services/courtService';
import pricingService from '../../services/pricingService';
import OwnerLayout from '../../components/Layout/OwnerLayout';
import MediaGallery from '../../components/MediaGallery/MediaGallery';
import PricingModal from '../../components/Pricing/PricingModal';
import './court.css';

const DAYS_MAP = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const CourtDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [court, setCourt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('info');
  const [pricingRules, setPricingRules] = useState([]);
  const [pricingLoading, setPricingLoading] = useState(false);
  const [showPricingModal, setShowPricingModal] = useState(false);
  const [editingPricing, setEditingPricing] = useState(null);

  useEffect(() => {
    if (id) {
      fetchCourt();
      if (activeTab === 'pricing') {
        fetchPricing();
      }
    }
  }, [id, activeTab]);

  const fetchCourt = async () => {
    try {
      setLoading(true);
      setError('');
      const result = await courtService.getCourtDetails(id);

      if (result.success && result.data) {
        setCourt(result.data);
      } else {
        setError('Court not found');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load court');
    } finally {
      setLoading(false);
    }
  };

  const fetchPricing = async () => {
    try {
      setPricingLoading(true);
      const result = await pricingService.getCourtPricing(id);
      if (result.success) {
        setPricingRules(result.data || []);
      }
    } catch (err) {
      console.error('Failed to load pricing:', err);
    } finally {
      setPricingLoading(false);
    }
  };

  const handleAddPricing = () => {
    setEditingPricing(null);
    setShowPricingModal(true);
  };

  const handleEditPricing = (pricing) => {
    setEditingPricing(pricing);
    setShowPricingModal(true);
  };

  const handlePricingSubmit = async (pricingData) => {
    try {
      if (editingPricing) {
        const result = await pricingService.updatePricing(editingPricing.id, pricingData);
        if (result.success) {
          fetchPricing();
          setShowPricingModal(false);
        } else {
          alert(result.message || 'Failed to update pricing');
        }
      } else {
        const result = await pricingService.createPricing(id, pricingData);
        if (result.success) {
          fetchPricing();
          setShowPricingModal(false);
        } else {
          alert(result.message || 'Failed to create pricing');
        }
      }
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to save pricing');
    }
  };

  const handleDeletePricing = async (pricingId) => {
    if (!window.confirm('Are you sure you want to delete this pricing rule?')) {
      return;
    }

    try {
      const result = await pricingService.deletePricing(pricingId);
      if (result.success) {
        fetchPricing();
      } else {
        alert(result.message || 'Failed to delete pricing');
      }
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to delete pricing');
    }
  };

  const handleDelete = async () => {
    if (
      !window.confirm(
        `Are you sure you want to delete "${court.name}"? This action cannot be undone.`
      )
    ) {
      return;
    }

    try {
      const result = await courtService.deleteCourt(id);

      if (result.success) {
        // Navigate back to property details
        navigate(`/owner/properties/${court.property_id}`);
      } else {
        alert(result.message || 'Failed to delete court');
      }
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to delete court');
    }
  };

  if (loading) {
    return (
      <OwnerLayout>
        <div className="ib-page-container">
          <div className="ib-page-header">
            <h1>Court Details</h1>
          </div>
          <div className="ib-page-content">
            <div className="ib-court-loading">Loading court...</div>
          </div>
        </div>
      </OwnerLayout>
    );
  }

  if (error || !court) {
    return (
      <OwnerLayout>
        <div className="ib-page-container">
          <div className="ib-page-header">
            <h1>Court Details</h1>
          </div>
          <div className="ib-page-content">
            <div className="ib-court-error-message">
              {error || 'Court not found'}
            </div>
          </div>
        </div>
      </OwnerLayout>
    );
  }

  return (
    <OwnerLayout>
      <div className="ib-page-container">
        <div className="ib-page-header">
          <h1>{court.name}</h1>
          <div style={{ display: 'flex', gap: '12px' }}>
            <Link
              to={`/owner/properties/${court.property_id}`}
              className="ib-btn-secondary"
            >
              Back to Property
            </Link>
            <Link to={`/owner/courts/${id}/edit`} className="ib-btn-primary">
              Edit Court
            </Link>
          </div>
        </div>

        <div className="ib-page-content">
          {/* Tabs */}
          <div className="ib-court-tabs">
            <button
              className={`ib-court-tab ${activeTab === 'info' ? 'active' : ''}`}
              onClick={() => setActiveTab('info')}
            >
              Information
            </button>
            <button
              className={`ib-court-tab ${activeTab === 'media' ? 'active' : ''}`}
              onClick={() => setActiveTab('media')}
            >
              Media
            </button>
            <button
              className={`ib-court-tab ${activeTab === 'pricing' ? 'active' : ''}`}
              onClick={() => setActiveTab('pricing')}
            >
              Pricing
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === 'info' && (
            <div className="ib-court-details-grid">
              {/* Court Information */}
              <div className="ib-court-info-card">
                <h2>Court Information</h2>

                <div className="ib-court-info-row">
                  <div className="ib-court-info-label">Status</div>
                  <div className="ib-court-info-value">
                    <span
                      className={`ib-property-status-badge ${
                        court.is_active ? 'active' : 'inactive'
                      }`}
                    >
                      {court.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>

                <div className="ib-court-info-row">
                  <div className="ib-court-info-label">Sport Type</div>
                  <div className="ib-court-info-value">{court.sport_type}</div>
                </div>

                {court.description && (
                  <div className="ib-court-info-row">
                    <div className="ib-court-info-label">Description</div>
                    <div className="ib-court-info-value">{court.description}</div>
                  </div>
                )}

                {court.specifications &&
                  Object.keys(court.specifications).length > 0 && (
                    <div className="ib-court-info-row">
                      <div className="ib-court-info-label">Specifications</div>
                      <div className="ib-court-info-value">
                        <div className="ib-court-spec-list">
                          {Object.entries(court.specifications).map(
                            ([key, value]) => (
                              <div key={key} className="ib-court-spec-item">
                                <strong>{key}:</strong> {value}
                              </div>
                            )
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                {court.amenities && court.amenities.length > 0 && (
                  <div className="ib-court-info-row">
                    <div className="ib-court-info-label">Amenities</div>
                    <div className="ib-court-info-value">
                      <div className="ib-court-amenities">
                        {court.amenities.map((amenity, index) => (
                          <span key={index} className="ib-court-amenity-tag">
                            {amenity}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Danger Zone */}
              <div className="ib-court-info-card">
                <h2 style={{ color: 'var(--color-error)' }}>Danger Zone</h2>
                <div className="ib-court-info-row">
                  <div className="ib-court-info-label">Delete Court</div>
                  <div className="ib-court-info-value">
                    <button
                      onClick={handleDelete}
                      className="ib-property-btn-delete"
                      style={{ width: 'auto' }}
                    >
                      Delete This Court
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'media' && (
            <div className="ib-court-info-card">
              <MediaGallery type="court" id={id} />
            </div>
          )}

          {activeTab === 'pricing' && (
            <div className="ib-court-info-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2>Pricing Rules</h2>
                <button className="ib-btn-primary" onClick={handleAddPricing}>
                  Add Pricing Rule
                </button>
              </div>

              {pricingLoading ? (
                <div className="ib-court-loading">Loading pricing...</div>
              ) : pricingRules.length === 0 ? (
                <div className="ib-court-empty-state">
                  <p>No pricing rules configured yet.</p>
                  <p>Add pricing rules to set hourly rates for different days and times.</p>
                </div>
              ) : (
                <div className="ib-pricing-list">
                  {pricingRules.map((pricing) => (
                    <div key={pricing.id} className="ib-pricing-card">
                      <div className="ib-pricing-header">
                        <div>
                          {pricing.label && (
                            <div className="ib-pricing-label">{pricing.label}</div>
                          )}
                          <div className="ib-pricing-days">
                            {pricing.days.map(day => DAYS_MAP[day]).join(', ')}
                          </div>
                        </div>
                        <div className="ib-pricing-price">${pricing.price_per_hour}/hr</div>
                      </div>
                      <div className="ib-pricing-time">
                        {pricing.start_time} - {pricing.end_time}
                      </div>
                      <div className="ib-pricing-actions">
                        <button
                          className="ib-btn-secondary"
                          onClick={() => handleEditPricing(pricing)}
                        >
                          Edit
                        </button>
                        <button
                          className="ib-property-btn-delete"
                          onClick={() => handleDeletePricing(pricing.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <PricingModal
          isOpen={showPricingModal}
          onClose={() => setShowPricingModal(false)}
          onSubmit={handlePricingSubmit}
          initialData={editingPricing}
        />
      </div>
    </OwnerLayout>
  );
};

export default CourtDetails;

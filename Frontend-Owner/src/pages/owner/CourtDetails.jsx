import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { courtService } from '../../services/courtService';
import pricingService from '../../services/pricingService';
import OwnerLayout from '../../components/Layout/OwnerLayout';
import MediaGallery from '../../components/MediaGallery/MediaGallery';
import PricingModal from '../../components/Pricing/PricingModal';
import PricingCard from '../../components/Pricing/PricingCard';
import './court.css';
import './courtDetailsNew.css';

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
  const [pricingError, setPricingError] = useState(null);
  const [pricingSuccess, setPricingSuccess] = useState(null);

  // Group pricing rules by day category
  const groupPricingRules = (rules) => {
    const groups = {
      friday: [],
      weekend: [],
      weekdays: [],
      custom: []
    };

    rules.forEach((rule, index) => {
      const ruleWithNumber = { ...rule, pricing_number: index + 1 };
      const dayNames = rule.days.map(d => DAYS_MAP[d]);
      
      // Friday only
      if (dayNames.length === 1 && dayNames.includes('Fri')) {
        groups.friday.push(ruleWithNumber);
      }
      // Weekend (Sat or Sun)
      else if (dayNames.some(d => d === 'Sat' || d === 'Sun')) {
        groups.weekend.push(ruleWithNumber);
      }
      // Weekdays only (Mon-Thu, no Fri)
      else if (dayNames.every(d => ['Mon', 'Tue', 'Wed', 'Thu'].includes(d))) {
        groups.weekdays.push(ruleWithNumber);
      }
      // Custom combination
      else {
        groups.custom.push(ruleWithNumber);
      }
    });

    return groups;
  };

  // Calculate pricing stats
  const calculatePricingStats = (rules) => {
    if (rules.length === 0) {
      return {
        totalRules: 0,
        daysCovered: '0/7',
        priceRange: 'N/A'
      };
    }

    // Count unique days covered
    const allDays = new Set();
    rules.forEach(rule => {
      rule.days.forEach(day => allDays.add(day));
    });

    // Find price range
    const prices = rules.map(r => r.price_per_hour);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);

    const formatPrice = (price) => {
      if (price >= 1000) {
        return `${Math.floor(price / 1000)}K`;
      }
      return price.toString();
    };

    return {
      totalRules: rules.length,
      daysCovered: `${allDays.size}/7`,
      priceRange: minPrice === maxPrice 
        ? `PKR ${formatPrice(minPrice)}` 
        : `PKR ${formatPrice(minPrice)}–${formatPrice(maxPrice)}`
    };
  };

  useEffect(() => {
    if (id) {
      fetchCourt();
    }
  }, [id]);

  useEffect(() => {
    if (id && activeTab === 'pricing') {
      fetchPricing();
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
    setPricingError(null);
    setPricingSuccess(null);
    setShowPricingModal(true);
  };

  const handleEditPricing = (pricing) => {
    setEditingPricing(pricing);
    setPricingError(null);
    setPricingSuccess(null);
    setShowPricingModal(true);
  };

  const handlePricingSubmit = async (pricingData) => {
    try {
      setPricingError(null);
      setPricingSuccess(null);
      
      if (editingPricing) {
        // Update single pricing rule
        const result = await pricingService.updatePricing(editingPricing.id, pricingData);
        if (result.success) {
          await fetchPricing();
          setShowPricingModal(false);
          setEditingPricing(null);
          setPricingSuccess('Pricing rule updated successfully!');
          setTimeout(() => setPricingSuccess(null), 5000);
        } else {
          setPricingError(result.message || 'Failed to update pricing');
        }
      } else {
        // Create pricing rule(s)
        if (pricingData.multiple && pricingData.rules) {
          // Create multiple pricing rules
          let successCount = 0;
          let failCount = 0;
          const conflictErrors = [];
          let otherError = null;
          
          for (const rule of pricingData.rules) {
            try {
              console.log('Creating pricing rule:', rule);
              const result = await pricingService.createPricing(id, rule);
              console.log('Result:', result);
              if (result.success) {
                successCount++;
              } else {
                failCount++;
                otherError = result.message;
              }
            } catch (err) {
              console.error('Error creating pricing rule:', err);
              console.error('Error response:', err.response?.data);
              failCount++;
              
              // Check if it's a conflict error (409)
              if (err.response?.status === 409) {
                const errorDetail = err.response?.data?.detail || '';
                conflictErrors.push(errorDetail);
              } else {
                otherError = err.response?.data?.detail || err.response?.data?.message || err.message;
              }
            }
          }
          
          if (successCount > 0) {
            await fetchPricing();
            setShowPricingModal(false);
            
            if (failCount > 0) {
              let errorParts = [];
              
              if (conflictErrors.length > 0) {
                const conflictMessages = conflictErrors.map((err) => {
                  // Extract pricing number from error message if available
                  const match = err.match(/pricing rule #(\d+)/i) || err.match(/existing.*?(\d+)/);
                  if (match) {
                    return `This time slot overlaps with Pricing #${match[1]}`;
                  }
                  return err;
                });
                errorParts.push(`Time Slot Conflicts: ${conflictMessages.join(', ')}`);
              }
              
              if (otherError) {
                errorParts.push(otherError);
              }
              
              setPricingError(`Created ${successCount} pricing rule(s), but ${failCount} failed. ${errorParts.join('. ')}`);
              setPricingSuccess(`Successfully created ${successCount} pricing rule(s)!`);
              setTimeout(() => {
                setPricingError(null);
                setPricingSuccess(null);
              }, 8000);
            } else {
              setPricingSuccess(`Successfully created ${successCount} pricing rule(s)!`);
              setTimeout(() => setPricingSuccess(null), 5000);
            }
          } else {
            let errorParts = [];
            
            if (conflictErrors.length > 0) {
              const conflictMessages = conflictErrors.map((err) => {
                const match = err.match(/pricing rule #(\d+)/i) || err.match(/existing.*?(\d+)/);
                if (match) {
                  return `Pricing #${match[1]}`;
                }
                return 'an existing pricing rule';
              });
              errorParts.push(`Time slot conflicts with: ${conflictMessages.join(', ')}`);
            } else if (otherError) {
              errorParts.push(otherError);
            }
            
            setPricingError(`Failed to create pricing rules. ${errorParts.join('. ')}. Please choose different time slots or edit the existing pricing rule.`);
          }
        } else {
          // Create single pricing rule
          console.log('Creating single pricing rule:', pricingData);
          const result = await pricingService.createPricing(id, pricingData);
          console.log('Result:', result);
          if (result.success) {
            await fetchPricing();
            setShowPricingModal(false);
            setPricingSuccess('Pricing rule created successfully!');
            setTimeout(() => setPricingSuccess(null), 5000);
          } else {
            setPricingError(result.message || 'Failed to create pricing');
          }
        }
      }
    } catch (err) {
      console.error('Error in handlePricingSubmit:', err);
      console.error('Error response:', err.response?.data);
      
      // Handle conflict error
      if (err.response?.status === 409) {
        const errorDetail = err.response?.data?.detail || '';
        const match = errorDetail.match(/pricing rule #(\d+)/i) || errorDetail.match(/existing.*?(\d+)/);
        
        if (match) {
          setPricingError(`⚠️ Time Slot Conflict: This time slot overlaps with Pricing #${match[1]}. Please choose different time slots or edit the existing pricing rule.`);
        } else {
          setPricingError(`⚠️ Time Slot Conflict: ${errorDetail}. Please choose different time slots or edit the existing pricing rule.`);
        }
      } else {
        setPricingError(err.response?.data?.detail || err.response?.data?.message || 'Failed to save pricing');
      }
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
        navigate(`/properties/${court.property_id}`);
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
      <div className="ch-court-details">
        {/* Topbar */}
        <div className="ch-topbar">
          <div className="ch-topbar-left">
            <span className="ch-breadcrumb">Courts ›</span>
            <h1 className="ch-page-title">{court.name}</h1>
          </div>
          <div className="ch-topbar-right">
            <Link
              to={`/properties/${court.property_id}`}
              className="ch-btn-ghost"
            >
              ← Back to Property
            </Link>
            <Link to={`/courts/${id}/edit`} className="ch-btn-primary">
              ✏️ Edit Court
            </Link>
          </div>
        </div>

        <div className="ch-content">
          {/* Tab Bar */}
          <div className="ch-tabs-container">
            <div className="ch-tabs">
              <button
                className={`ch-tab ${activeTab === 'info' ? 'active' : ''}`}
                onClick={() => setActiveTab('info')}
              >
                Information
              </button>
              <button
                className={`ch-tab ${activeTab === 'media' ? 'active' : ''}`}
                onClick={() => setActiveTab('media')}
              >
                Media
              </button>
              <button
                className={`ch-tab ${activeTab === 'pricing' ? 'active' : ''}`}
                onClick={() => setActiveTab('pricing')}
              >
                Pricing
              </button>
            </div>
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
            <div className="ch-pricing-container">
              {/* Summary Stats Bar */}
              {pricingRules.length > 0 && (
                <div className="ch-pricing-stats">
                  <div className="ch-stat-card">
                    <div className="ch-stat-icon ch-stat-icon-green">💰</div>
                    <div className="ch-stat-content">
                      <div className="ch-stat-number">{calculatePricingStats(pricingRules).totalRules}</div>
                      <div className="ch-stat-label">Pricing Rules</div>
                    </div>
                  </div>
                  <div className="ch-stat-card">
                    <div className="ch-stat-icon ch-stat-icon-blue">📆</div>
                    <div className="ch-stat-content">
                      <div className="ch-stat-number">{calculatePricingStats(pricingRules).daysCovered}</div>
                      <div className="ch-stat-label">Days Covered</div>
                    </div>
                  </div>
                  <div className="ch-stat-card">
                    <div className="ch-stat-icon ch-stat-icon-amber">📈</div>
                    <div className="ch-stat-content">
                      <div className="ch-stat-number">{calculatePricingStats(pricingRules).priceRange}</div>
                      <div className="ch-stat-label">Price Range / hr</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Section Header */}
              <div className="ch-pricing-header">
                <div className="ch-pricing-header-left">
                  <h2 className="ch-pricing-title">Pricing Rules</h2>
                  {pricingRules.length > 0 && (
                    <span className="ch-pricing-badge">{pricingRules.length} rules</span>
                  )}
                </div>
                <button className="ch-btn-add-pricing" onClick={handleAddPricing}>
                  + Add Pricing Rule
                </button>
              </div>

              {/* Error/Success Messages */}
              {pricingError && (
                <div className="ch-pricing-error-message">
                  ⚠️ {pricingError}
                </div>
              )}

              {pricingSuccess && (
                <div className="ch-pricing-success-message">
                  ✓ {pricingSuccess}
                </div>
              )}

              {/* Pricing Rules Content */}
              {pricingLoading ? (
                <div className="ch-pricing-loading">Loading pricing...</div>
              ) : pricingRules.length === 0 ? (
                <div className="ch-pricing-empty">
                  <div className="ch-pricing-empty-icon">📋</div>
                  <h3>No pricing rules configured yet</h3>
                  <p>Add pricing rules to set hourly rates for different days and times.</p>
                  <button className="ch-btn-add-pricing-empty" onClick={handleAddPricing}>
                    + Add Your First Pricing Rule
                  </button>
                </div>
              ) : (
                <div className="ch-pricing-groups">
                  {(() => {
                    const groups = groupPricingRules(pricingRules);
                    
                    return (
                      <>
                        {/* Friday Group */}
                        {groups.friday.length > 0 && (
                          <div className="ch-pricing-group">
                            <div className="ch-pricing-group-header">
                              <span className="ch-pricing-group-label">FRIDAY</span>
                              <div className="ch-pricing-group-line"></div>
                            </div>
                            <div className="ch-pricing-group-cards">
                              {groups.friday.map(pricing => (
                                <PricingCard
                                  key={pricing.id}
                                  pricing={pricing}
                                  pricingNumber={pricing.pricing_number}
                                  onEdit={handleEditPricing}
                                  onDelete={handleDeletePricing}
                                />
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Weekend Group */}
                        {groups.weekend.length > 0 && (
                          <div className="ch-pricing-group">
                            <div className="ch-pricing-group-header">
                              <span className="ch-pricing-group-label">WEEKEND</span>
                              <div className="ch-pricing-group-line"></div>
                            </div>
                            <div className="ch-pricing-group-cards">
                              {groups.weekend.map(pricing => (
                                <PricingCard
                                  key={pricing.id}
                                  pricing={pricing}
                                  pricingNumber={pricing.pricing_number}
                                  onEdit={handleEditPricing}
                                  onDelete={handleDeletePricing}
                                />
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Weekdays Group */}
                        {groups.weekdays.length > 0 && (
                          <div className="ch-pricing-group">
                            <div className="ch-pricing-group-header">
                              <span className="ch-pricing-group-label">WEEKDAYS</span>
                              <div className="ch-pricing-group-line"></div>
                            </div>
                            <div className="ch-pricing-group-cards">
                              {groups.weekdays.map(pricing => (
                                <PricingCard
                                  key={pricing.id}
                                  pricing={pricing}
                                  pricingNumber={pricing.pricing_number}
                                  onEdit={handleEditPricing}
                                  onDelete={handleDeletePricing}
                                />
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Custom Group */}
                        {groups.custom.length > 0 && (
                          <div className="ch-pricing-group">
                            <div className="ch-pricing-group-header">
                              <span className="ch-pricing-group-label">CUSTOM</span>
                              <div className="ch-pricing-group-line"></div>
                            </div>
                            <div className="ch-pricing-group-cards">
                              {groups.custom.map(pricing => (
                                <PricingCard
                                  key={pricing.id}
                                  pricing={pricing}
                                  pricingNumber={pricing.pricing_number}
                                  onEdit={handleEditPricing}
                                  onDelete={handleDeletePricing}
                                />
                              ))}
                            </div>
                          </div>
                        )}
                      </>
                    );
                  })()}

                  {/* Add Rule Dashed Card */}
                  <button className="ch-pricing-add-card" onClick={handleAddPricing}>
                    <span className="ch-pricing-add-icon">+</span>
                    <span className="ch-pricing-add-text">Add another pricing rule</span>
                  </button>
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

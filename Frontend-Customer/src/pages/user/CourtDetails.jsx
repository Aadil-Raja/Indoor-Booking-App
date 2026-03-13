import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import UserLayout from '../../components/Layout/UserLayout';
import { publicService } from '../../services/publicService';
import './courtDetails.css';

const CourtDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [court, setCourt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState(0);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchCourtDetails();
  }, [id]);

  const fetchCourtDetails = async () => {
    try {
      setLoading(true);
      const result = await publicService.getCourtDetails(id);
      
      if (result.success && result.data) {
        setCourt(result.data);
      } else {
        setError('Court not found');
      }
    } catch (err) {
      console.error('Failed to load court details:', err);
      setError('Failed to load court details');
    } finally {
      setLoading(false);
    }
  };

  const formatPrice = (price) => {
    return price ? price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '0';
  };

  if (loading) {
    return (
      <UserLayout>
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading court details...</p>
        </div>
      </UserLayout>
    );
  }

  if (error || !court) {
    return (
      <UserLayout>
        <div className="error-container">
          <div className="error-icon">⚠️</div>
          <h2>{error || 'Court not found'}</h2>
          <button onClick={() => navigate('/dashboard')} className="btn-back">
            Back to Search
          </button>
        </div>
      </UserLayout>
    );
  }

  const images = court.media?.filter(m => m.media_type === 'image') || [];
  const videos = court.media?.filter(m => m.media_type === 'video') || [];

  return (
    <UserLayout>
      <div className="court-details">
        {/* Back Button */}
        <button onClick={() => navigate('/dashboard')} className="back-btn">
          ← Back to Search
        </button>

        {/* Image Gallery */}
        <div className="gallery-section">
          <div className="main-image">
            {images.length > 0 ? (
              <img 
                src={images[selectedImage]?.url} 
                alt={court.name}
                onError={(e) => {
                  e.target.src = 'https://via.placeholder.com/800x500?text=Court+Image';
                }}
              />
            ) : (
              <div className="image-placeholder">
                <span>🏟️</span>
                <p>No images available</p>
              </div>
            )}
          </div>
          
          {images.length > 1 && (
            <div className="thumbnail-strip">
              {images.map((img, index) => (
                <div
                  key={index}
                  className={`thumbnail ${selectedImage === index ? 'active' : ''}`}
                  onClick={() => setSelectedImage(index)}
                >
                  <img 
                    src={img.url} 
                    alt={`${court.name} ${index + 1}`}
                    onError={(e) => {
                      e.target.src = 'https://via.placeholder.com/150?text=Image';
                    }}
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Court Info */}
        <div className="details-grid">
          <div className="details-main">
            <div className="court-header">
              <div>
                <h1 className="court-title">{court.name}</h1>
                <p className="court-location">
                  📍 {court.property?.address || 'Location not specified'}
                </p>
              </div>
              <div className="court-price-box">
                <span className="price-label">Starting from</span>
                <span className="price-amount">PKR {formatPrice(court.base_price)}/hr</span>
              </div>
            </div>

            <div className="court-tags">
              <span className="tag tag-primary">{court.sport_type}</span>
              <span className="tag">{court.surface_type}</span>
              <span className="tag">{court.is_indoor ? '🏠 Indoor' : '☀️ Outdoor'}</span>
            </div>

            {court.description && (
              <div className="section">
                <h2 className="section-title">About this Court</h2>
                <p className="section-text">{court.description}</p>
              </div>
            )}

            <div className="section">
              <h2 className="section-title">Court Specifications</h2>
              <div className="specs-grid">
                <div className="spec-item">
                  <span className="spec-icon">📏</span>
                  <div>
                    <div className="spec-label">Dimensions</div>
                    <div className="spec-value">
                      {court.length}m × {court.width}m
                    </div>
                  </div>
                </div>
                <div className="spec-item">
                  <span className="spec-icon">🎯</span>
                  <div>
                    <div className="spec-label">Surface</div>
                    <div className="spec-value">{court.surface_type}</div>
                  </div>
                </div>
                <div className="spec-item">
                  <span className="spec-icon">⚽</span>
                  <div>
                    <div className="spec-label">Sport</div>
                    <div className="spec-value">{court.sport_type}</div>
                  </div>
                </div>
                <div className="spec-item">
                  <span className="spec-icon">{court.is_indoor ? '🏠' : '☀️'}</span>
                  <div>
                    <div className="spec-label">Type</div>
                    <div className="spec-value">{court.is_indoor ? 'Indoor' : 'Outdoor'}</div>
                  </div>
                </div>
              </div>
            </div>

            {videos.length > 0 && (
              <div className="section">
                <h2 className="section-title">Videos</h2>
                <div className="videos-grid">
                  {videos.map((video, index) => (
                    <div key={index} className="video-item">
                      <video controls>
                        <source src={video.url} type="video/mp4" />
                        Your browser does not support the video tag.
                      </video>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {court.property && (
              <div className="section">
                <h2 className="section-title">Property Information</h2>
                <div className="property-info">
                  <h3>{court.property.name}</h3>
                  <p>📍 {court.property.address}</p>
                  {court.property.description && (
                    <p className="property-desc">{court.property.description}</p>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Booking Sidebar */}
          <div className="booking-sidebar">
            <div className="booking-card">
              <h3 className="booking-title">Ready to Book?</h3>
              <p className="booking-subtitle">Select your preferred date and time</p>
              
              <div className="price-display">
                <span className="price-from">From</span>
                <span className="price-big">PKR {formatPrice(court.base_price)}</span>
                <span className="price-per">per hour</span>
              </div>

              <button
                onClick={() => navigate(`/courts/${court.id}/book`)}
                className="btn-book-now"
              >
                Book Now →
              </button>

              <div className="booking-features">
                <div className="feature">✓ Instant confirmation</div>
                <div className="feature">✓ Flexible cancellation</div>
                <div className="feature">✓ Secure payment</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </UserLayout>
  );
};

export default CourtDetails;

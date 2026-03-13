import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { propertyService } from '../../services/propertyService';
import OwnerLayout from '../../components/Layout/OwnerLayout';
import './court.css';

const CourtList = () => {
  const [courts, setCourts] = useState([]);
  const [filteredCourts, setFilteredCourts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchAllCourts();
  }, []);

  useEffect(() => {
    if (searchTerm) {
      const filtered = courts.filter(
        (court) =>
          court.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          court.sport_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
          court.property_name.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredCourts(filtered);
    } else {
      setFilteredCourts(courts);
    }
  }, [searchTerm, courts]);

  const fetchAllCourts = async () => {
    try {
      setLoading(true);
      setError('');
      
      // Get all properties first
      const propertiesResult = await propertyService.getProperties();
      
      if (propertiesResult.success) {
        const properties = propertiesResult.data || [];
        
        // Fetch details for each property to get courts
        const allCourts = [];
        for (const property of properties) {
          try {
            const detailsResult = await propertyService.getPropertyDetails(property.id);
            if (detailsResult.success && detailsResult.data.courts) {
              detailsResult.data.courts.forEach(court => {
                allCourts.push({
                  ...court,
                  property_id: property.id,
                  property_name: property.name
                });
              });
            }
          } catch (err) {
            console.error(`Failed to fetch courts for property ${property.id}`);
          }
        }
        
        setCourts(allCourts);
      } else {
        setError('Failed to load courts');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load courts');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <OwnerLayout>
        <div className="ib-page-container">
          <div className="ib-page-header">
            <h1>All Courts</h1>
          </div>
          <div className="ib-page-content">
            <div className="ib-court-loading">Loading courts...</div>
          </div>
        </div>
      </OwnerLayout>
    );
  }

  return (
    <OwnerLayout>
      <div className="ib-page-container">
        <div className="ib-page-header">
          <h1>All Courts</h1>
        </div>

        <div className="ib-page-content">
          {error && <div className="ib-court-error-message">{error}</div>}

          {courts.length > 0 && (
            <div className="ib-property-search">
              <input
                type="text"
                placeholder="Search courts by name, sport type, or property..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          )}

          {filteredCourts.length === 0 ? (
            <div className="ib-court-empty-state">
              <h2>No Courts Found</h2>
              <p>
                {searchTerm
                  ? 'No courts match your search.'
                  : 'You haven\'t added any courts yet.'}
              </p>
              {!searchTerm && (
                <Link
                  to="/properties"
                  className="ib-btn-primary"
                  style={{ marginTop: '1rem' }}
                >
                  Go to Properties to Add Courts
                </Link>
              )}
            </div>
          ) : (
            <div className="ib-court-list-grid">
              {filteredCourts.map((court) => (
                <div key={court.id} className="ib-court-list-card">
                  <div className="ib-court-card-header">
                    <div>
                      <h3>{court.name}</h3>
                      <p className="ib-court-sport-type">{court.sport_type}</p>
                    </div>
                    <span
                      className={`ib-property-status-badge ${
                        court.is_active ? 'active' : 'inactive'
                      }`}
                    >
                      {court.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>

                  <div className="ib-court-property-label">
                    <span className="ib-court-property-icon">▣</span>
                    <Link
                      to={`/properties/${court.property_id}`}
                      className="ib-court-property-link"
                    >
                      {court.property_name}
                    </Link>
                  </div>

                  <div className="ib-court-card-actions">
                    <Link
                      to={`/courts/${court.id}`}
                      className="ib-property-btn-view"
                    >
                      View Details
                    </Link>
                    <Link
                      to={`/courts/${court.id}/edit`}
                      className="ib-property-btn-edit"
                    >
                      Edit
                    </Link>
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

export default CourtList;

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import UserLayout from '../../components/Layout/UserLayout';
import { bookingService } from '../../services/bookingService';
import './userBookings.css';

const UserBookings = () => {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, pending, confirmed, cancelled
  const navigate = useNavigate();

  useEffect(() => {
    fetchBookings();
  }, [filter]);

  const fetchBookings = async () => {
    try {
      setLoading(true);
      const params = filter !== 'all' ? { status: filter } : {};
      const result = await bookingService.getUserBookings(params);
      
      if (result.success && result.data) {
        setBookings(result.data);
      }
    } catch (err) {
      console.error('Failed to load bookings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelBooking = async (bookingId) => {
    if (!confirm('Are you sure you want to cancel this booking?')) return;

    try {
      const result = await bookingService.cancelBooking(bookingId);
      if (result.success) {
        fetchBookings();
      }
    } catch (err) {
      console.error('Failed to cancel booking:', err);
      alert('Failed to cancel booking');
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatTime = (timeString) => {
    if (!timeString) return '';
    const [hours, minutes] = timeString.split(':');
    const hour = parseInt(hours);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour % 12 || 12;
    return `${displayHour}:${minutes} ${ampm}`;
  };

  const formatPrice = (price) => {
    return price ? price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '0';
  };

  const getStatusBadge = (status) => {
    const badges = {
      pending: { class: 'status-pending', text: 'Pending', color: '#f59e0b' },
      confirmed: { class: 'status-confirmed', text: 'Confirmed', color: '#16a34a' },
      cancelled: { class: 'status-cancelled', text: 'Cancelled', color: '#ef4444' },
      completed: { class: 'status-completed', text: 'Completed', color: '#6366f1' }
    };
    return badges[status] || badges.pending;
  };

  return (
    <UserLayout>
      <div className="user-bookings">
        <div className="bookings-header">
          <div>
            <h1 className="page-title">My Bookings</h1>
            <p className="page-subtitle">View and manage your court bookings</p>
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            className="btn-new-booking"
          >
            + New Booking
          </button>
        </div>

        {/* Filter Tabs */}
        <div className="filter-tabs">
          <button
            onClick={() => setFilter('all')}
            className={`filter-tab ${filter === 'all' ? 'active' : ''}`}
          >
            All Bookings
          </button>
          <button
            onClick={() => setFilter('pending')}
            className={`filter-tab ${filter === 'pending' ? 'active' : ''}`}
          >
            Pending
          </button>
          <button
            onClick={() => setFilter('confirmed')}
            className={`filter-tab ${filter === 'confirmed' ? 'active' : ''}`}
          >
            Confirmed
          </button>
          <button
            onClick={() => setFilter('cancelled')}
            className={`filter-tab ${filter === 'cancelled' ? 'active' : ''}`}
          >
            Cancelled
          </button>
        </div>

        {/* Bookings List */}
        {loading ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading bookings...</p>
          </div>
        ) : bookings.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon"></div>
            <h3>No bookings found</h3>
            <p>You haven't made any bookings yet</p>
            <button
              onClick={() => navigate('/dashboard')}
              className="btn-browse"
            >
              Browse Courts
            </button>
          </div>
        ) : (
          <div className="bookings-list">
            {bookings.map((booking) => {
              const status = getStatusBadge(booking.status);
              return (
                <div key={booking.id} className="booking-card">
                  <div className="booking-main-info">
                    <div className="court-info">
                      {booking.court?.media?.[0] && (
                        <div className="court-thumb">
                          <img
                            src={booking.court.media[0].url}
                            alt={booking.court.name}
                            onError={(e) => {
                              e.target.src = 'https://via.placeholder.com/100?text=Court';
                            }}
                          />
                        </div>
                      )}
                      <div className="court-details">
                        <h3 className="court-name">{booking.court?.name || 'Court'}</h3>
                        <p className="court-location">
                          {booking.court?.property?.address || 'Location'}
                        </p>
                      </div>
                    </div>

                    <div className="booking-details">
                      <div className="detail-item">
                        <span className="detail-icon"></span>
                        <div>
                          <div className="detail-label">Date</div>
                          <div className="detail-value">{formatDate(booking.booking_date)}</div>
                        </div>
                      </div>

                      <div className="detail-item">
                        <span className="detail-icon"></span>
                        <div>
                          <div className="detail-label">Time</div>
                          <div className="detail-value">
                            {formatTime(booking.start_time)} - {formatTime(booking.end_time)}
                          </div>
                        </div>
                      </div>

                      <div className="detail-item">
                        <span className="detail-icon"></span>
                        <div>
                          <div className="detail-label">Duration</div>
                          <div className="detail-value">
                            {booking.total_hours} {booking.total_hours === 1 ? 'Hour' : 'Hours'}
                          </div>
                        </div>
                      </div>

                      <div className="detail-item">
                        <span className="detail-icon"></span>
                        <div>
                          <div className="detail-label">Total</div>
                          <div className="detail-value">PKR {formatPrice(booking.total_price)}</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="booking-footer">
                    <span className={`status-badge ${status.class}`}>
                      {status.text}
                    </span>

                    <div className="booking-actions">
                      <button
                        onClick={() => navigate(`/courts/${booking.court_id}`)}
                        className="btn-view-court"
                      >
                        View Court
                      </button>
                      {booking.status === 'pending' && (
                        <button
                          onClick={() => handleCancelBooking(booking.id)}
                          className="btn-cancel"
                        >
                          Cancel
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </UserLayout>
  );
};

export default UserBookings;

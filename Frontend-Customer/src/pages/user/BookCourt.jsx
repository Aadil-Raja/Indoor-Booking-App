import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import UserLayout from '../../components/Layout/UserLayout';
import { publicService } from '../../services/publicService';
import { bookingService } from '../../services/bookingService';
import './bookCourt.css';

const BookCourt = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [court, setCourt] = useState(null);
  const [selectedDate, setSelectedDate] = useState(getTodayDate());
  const [availableSlots, setAvailableSlots] = useState([]);
  const [selectedSlots, setSelectedSlots] = useState([]); // Multiple slots
  const [paymentFile, setPaymentFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [bookingLoading, setBookingLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  function getTodayDate() {
    const today = new Date();
    return today.toISOString().split('T')[0];
  }

  useEffect(() => {
    fetchCourtDetails();
  }, [id]);

  useEffect(() => {
    if (selectedDate) {
      fetchAvailableSlots();
    }
  }, [selectedDate]);

  const fetchCourtDetails = async () => {
    try {
      setLoading(true);
      const result = await publicService.getCourtDetails(id);
      
      if (result.success && result.data) {
        setCourt(result.data);
      }
    } catch (err) {
      console.error('Failed to load court:', err);
      setError('Failed to load court details');
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableSlots = async () => {
    try {
      const result = await publicService.getAvailableSlots(id, selectedDate);
      
      if (result.success && result.data) {
        setAvailableSlots(result.data.available_slots || []);
      } else {
        setAvailableSlots([]);
      }
    } catch (err) {
      console.error('Failed to load slots:', err);
      if (err.response?.status === 404) {
        setError('This court is not available on the selected date. Please try another date.');
      }
      setAvailableSlots([]);
    }
  };

  const handleSlotClick = (slot) => {
    const slotKey = `${slot.start_time}-${slot.end_time}`;
    const isSelected = selectedSlots.some(s => `${s.start_time}-${s.end_time}` === slotKey);
    
    if (isSelected) {
      // Deselect
      setSelectedSlots(selectedSlots.filter(s => `${s.start_time}-${s.end_time}` !== slotKey));
    } else {
      // Select
      setSelectedSlots([...selectedSlots, slot]);
    }
    setError('');
  };

  const handleSlotMouseDown = (slot) => {
    setIsDragging(true);
    handleSlotClick(slot);
  };

  const handleSlotMouseEnter = (slot) => {
    if (isDragging) {
      const slotKey = `${slot.start_time}-${slot.end_time}`;
      const isSelected = selectedSlots.some(s => `${s.start_time}-${s.end_time}` === slotKey);
      
      if (!isSelected) {
        setSelectedSlots([...selectedSlots, slot]);
      }
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  useEffect(() => {
    document.addEventListener('mouseup', handleMouseUp);
    return () => document.removeEventListener('mouseup', handleMouseUp);
  }, []);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        setError('File size should be less than 5MB');
        return;
      }
      setPaymentFile(file);
      setError('');
    }
  };

  const calculateTotal = () => {
    if (!selectedSlots.length) return 0;
    
    const totalPrice = selectedSlots.reduce((sum, slot) => {
      return sum + (slot.price_per_hour || 0);
    }, 0);
    
    return totalPrice;
  };

  const getTotalHours = () => {
    return selectedSlots.length;
  };

  const getTimeRange = () => {
    if (selectedSlots.length === 0) return '';
    
    // Sort slots by start time
    const sorted = [...selectedSlots].sort((a, b) => 
      a.start_time.localeCompare(b.start_time)
    );
    
    const firstSlot = sorted[0];
    const lastSlot = sorted[sorted.length - 1];
    
    return `${formatTime(firstSlot.start_time)} - ${formatTime(lastSlot.end_time)}`;
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const formatTime = (timeString) => {
    const [hours, minutes] = timeString.split(':');
    const hour = parseInt(hours);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour % 12 || 12;
    return `${displayHour}:${minutes} ${ampm}`;
  };

  const formatPrice = (price) => {
    return price ? price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '0';
  };

  const changeDate = (days) => {
    const currentDate = new Date(selectedDate);
    currentDate.setDate(currentDate.getDate() + days);
    
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    if (currentDate >= today) {
      setSelectedDate(currentDate.toISOString().split('T')[0]);
      setSelectedSlots([]); // Clear selections when date changes
    }
  };

  const handleDateChange = (e) => {
    setSelectedDate(e.target.value);
    setShowDatePicker(false);
    setSelectedSlots([]); // Clear selections when date changes
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (selectedSlots.length === 0) {
      setError('Please select at least one time slot');
      return;
    }

    if (!paymentFile) {
      setError('Please upload payment screenshot');
      return;
    }

    try {
      setBookingLoading(true);
      setError('');

      // Sort slots to get start and end time
      const sorted = [...selectedSlots].sort((a, b) => 
        a.start_time.localeCompare(b.start_time)
      );

      const bookingData = {
        court_id: parseInt(id),
        booking_date: selectedDate,
        start_time: sorted[0].start_time,
        end_time: sorted[sorted.length - 1].end_time,
        payment_screenshot: paymentFile
      };

      const result = await bookingService.createBooking(bookingData);

      if (result.success) {
        setSuccess('Booking created successfully! Redirecting...');
        setTimeout(() => {
          navigate('/bookings');
        }, 2000);
      } else {
        setError(result.message || 'Failed to create booking');
      }
    } catch (err) {
      console.error('Booking error:', err);
      setError(err.response?.data?.message || 'Failed to create booking');
    } finally {
      setBookingLoading(false);
    }
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

  if (!court) {
    return (
      <UserLayout>
        <div className="error-container">
          <h2>Court not found</h2>
          <button onClick={() => navigate('/dashboard')} className="btn-primary">
            Back to Dashboard
          </button>
        </div>
      </UserLayout>
    );
  }

  return (
    <UserLayout>
      <div className="book-court-container">
        <div className="book-court-header">
          <button onClick={() => navigate(-1)} className="back-btn">
            ← Back to Court Details
          </button>
          <h1 className="page-title">Book {court.name}</h1>
          <p className="page-subtitle">Select your preferred date and time slots</p>
        </div>

        <div className="booking-layout">
          <div className="booking-main">
            {/* Date Selection */}
            <div className="booking-section">
              <h2 className="section-title">Select Date</h2>
              <div className="date-selector">
                <button
                  type="button"
                  onClick={() => changeDate(-1)}
                  className="date-nav-btn"
                >
                  ‹
                </button>
                <div className="date-display" onClick={() => setShowDatePicker(!showDatePicker)}>
                  {formatDate(selectedDate)}
                </div>
                <button
                  type="button"
                  onClick={() => changeDate(1)}
                  className="date-nav-btn"
                >
                  ›
                </button>
                <button
                  type="button"
                  onClick={() => setShowDatePicker(!showDatePicker)}
                  className="calendar-btn-book"
                >
                  Calendar
                </button>
              </div>
              {showDatePicker && (
                <div className="date-picker-inline">
                  <input
                    type="date"
                    value={selectedDate}
                    onChange={handleDateChange}
                    min={getTodayDate()}
                    className="date-picker-input-large"
                  />
                </div>
              )}
            </div>

            {/* Time Slots */}
            <div className="booking-section">
              <h2 className="section-title">Select Time Slots</h2>
              <p className="section-hint">Click or drag to select multiple slots</p>
              
              {availableSlots.length === 0 ? (
                <p className="no-slots">No slots available for this date</p>
              ) : (
                <div className="slots-grid-multi" onMouseLeave={handleMouseUp}>
                  {availableSlots.map((slot, index) => {
                    const slotKey = `${slot.start_time}-${slot.end_time}`;
                    const isSelected = selectedSlots.some(
                      s => `${s.start_time}-${s.end_time}` === slotKey
                    );
                    
                    return (
                      <button
                        key={index}
                        onMouseDown={() => handleSlotMouseDown(slot)}
                        onMouseEnter={() => handleSlotMouseEnter(slot)}
                        className={`slot-btn-multi ${isSelected ? 'selected' : ''}`}
                      >
                        <span className="slot-time-range">
                          {formatTime(slot.start_time)} - {formatTime(slot.end_time)}
                        </span>
                        <span className="slot-price">PKR {formatPrice(slot.price_per_hour)}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Payment Proof */}
            <div className="booking-section">
              <h2 className="section-title">Payment Proof</h2>
              <p className="section-hint">
                Upload a screenshot of your payment. Your booking will be confirmed once the owner verifies it.
              </p>
              <div className="file-upload-area">
                <input
                  type="file"
                  id="payment-file"
                  accept="image/*"
                  onChange={handleFileChange}
                  className="file-input"
                />
                <label htmlFor="payment-file" className="file-label">
                  <span className="file-icon">📎</span>
                  <span className="file-text">
                    {paymentFile ? paymentFile.name : 'Choose File'}
                  </span>
                </label>
              </div>
            </div>

            {error && <div className="error-message">{error}</div>}
            {success && <div className="success-message">{success}</div>}
          </div>

          {/* Booking Summary Sidebar */}
          <div className="booking-sidebar">
            <div className="booking-summary">
              <h3 className="summary-title">Booking Summary</h3>
              
              <div className="summary-item">
                <span className="summary-label">Court</span>
                <span className="summary-value">{court.name}</span>
              </div>

              <div className="summary-item">
                <span className="summary-label">Date</span>
                <span className="summary-value">{formatDate(selectedDate)}</span>
              </div>

              {selectedSlots.length > 0 && (
                <>
                  <div className="summary-item">
                    <span className="summary-label">Time</span>
                    <span className="summary-value">{getTimeRange()}</span>
                  </div>

                  <div className="summary-item">
                    <span className="summary-label">Duration</span>
                    <span className="summary-value">{getTotalHours()} Hour{getTotalHours() > 1 ? 's' : ''}</span>
                  </div>

                  <div className="summary-divider"></div>

                  <div className="summary-item summary-total">
                    <span className="summary-label">Total Amount</span>
                    <span className="summary-value">PKR {formatPrice(calculateTotal())}</span>
                  </div>
                </>
              )}

              <button
                onClick={handleSubmit}
                disabled={bookingLoading || selectedSlots.length === 0 || !paymentFile}
                className="btn-confirm-booking"
              >
                {bookingLoading ? 'Processing...' : 'Confirm Booking'}
              </button>

              <p className="booking-note">
                Your booking will be pending until the owner confirms your payment.
              </p>
            </div>
          </div>
        </div>
      </div>
    </UserLayout>
  );
};

export default BookCourt;

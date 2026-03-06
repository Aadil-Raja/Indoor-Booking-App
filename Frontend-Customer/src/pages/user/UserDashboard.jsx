import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import UserLayout from '../../components/Layout/UserLayout';
import { publicService } from '../../services/publicService';
import './userDashboard.css';

const UserDashboard = () => {
  const [courtName, setCourtName] = useState('');
  const [address, setAddress] = useState('');
  const [selectedDate, setSelectedDate] = useState(getTodayDate());
  const [selectedTimeSlots, setSelectedTimeSlots] = useState([]);
  const [selectedPeriod, setSelectedPeriod] = useState('all'); // 'all', 'am', 'pm'
  const [courts, setCourts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showTimeSlotPicker, setShowTimeSlotPicker] = useState(false);
  const navigate = useNavigate();
  
  const dateFilterRef = useRef(null);
  const timeFilterRef = useRef(null);

  function getTodayDate() {
    const today = new Date();
    return today.toISOString().split('T')[0];
  }

  // Check if a time slot is in the past
  const isSlotInPast = (slot) => {
    // If selected date is not today, no slots are in the past
    const today = getTodayDate();
    if (selectedDate !== today) {
      return false;
    }

    // Get current hour
    const now = new Date();
    const currentHour = now.getHours();

    // Convert slot to 24-hour format
    const [hour] = slot.value.split('-');
    let slotHour = parseInt(hour);
    
    if (slot.period === 'pm' && slotHour !== 12) {
      slotHour += 12;
    } else if (slot.period === 'am' && slotHour === 12) {
      slotHour = 0;
    }

    // Slot is in the past if its end time has passed
    const slotEndHour = slotHour + 1;
    return slotEndHour <= currentHour;
  };

  // Generate time slots (1-2, 2-3, etc.)
  const timeSlots = [
    { value: '1-2', label: '1-2', period: 'am' },
    { value: '2-3', label: '2-3', period: 'am' },
    { value: '3-4', label: '3-4', period: 'am' },
    { value: '4-5', label: '4-5', period: 'am' },
    { value: '5-6', label: '5-6', period: 'am' },
    { value: '6-7', label: '6-7', period: 'am' },
    { value: '7-8', label: '7-8', period: 'am' },
    { value: '8-9', label: '8-9', period: 'am' },
    { value: '9-10', label: '9-10', period: 'am' },
    { value: '10-11', label: '10-11', period: 'am' },
    { value: '11-12', label: '11-12', period: 'am' },
    { value: '12-1', label: '12-1', period: 'pm' },
    { value: '1-2', label: '1-2', period: 'pm' },
    { value: '2-3', label: '2-3', period: 'pm' },
    { value: '3-4', label: '3-4', period: 'pm' },
    { value: '4-5', label: '4-5', period: 'pm' },
    { value: '5-6', label: '5-6', period: 'pm' },
    { value: '6-7', label: '6-7', period: 'pm' },
    { value: '7-8', label: '7-8', period: 'pm' },
    { value: '8-9', label: '8-9', period: 'pm' },
    { value: '9-10', label: '9-10', period: 'pm' },
    { value: '10-11', label: '10-11', period: 'pm' },
    { value: '11-12', label: '11-12', period: 'pm' },
  ];

  useEffect(() => {
    fetchCourts();
  }, []);

  useEffect(() => {
    // Close dropdowns when clicking outside
    const handleClickOutside = (event) => {
      if (dateFilterRef.current && !dateFilterRef.current.contains(event.target)) {
        setShowDatePicker(false);
      }
      
      if (timeFilterRef.current && !timeFilterRef.current.contains(event.target)) {
        setShowTimeSlotPicker(false);
      }
    };

    if (showDatePicker || showTimeSlotPicker) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showDatePicker, showTimeSlotPicker]);

  const fetchCourts = async () => {
    try {
      setLoading(true);
      
      // Build search query from court name and address
      const searchTerms = [courtName, address].filter(Boolean).join(' ');
      
      // Convert selected time slots to start_time format for API
      let startTime = '';
      if (selectedTimeSlots.length > 0) {
        // Use the first selected slot for filtering
        const firstSlot = selectedTimeSlots[0];
        const [hour] = firstSlot.value.split('-');
        const slot = timeSlots.find(s => s.value === firstSlot.value && s.period === firstSlot.period);
        
        if (slot) {
          let hourNum = parseInt(hour);
          if (slot.period === 'pm' && hourNum !== 12) hourNum += 12;
          if (slot.period === 'am' && hourNum === 12) hourNum = 0;
          startTime = `${hourNum.toString().padStart(2, '0')}:00`;
        }
      }
      
      const result = await publicService.searchCourts({
        search: searchTerms,
        date: selectedDate,
        start_time: startTime
      });
      
      if (result.success && result.data && result.data.items) {
        setCourts(result.data.items);
      } else {
        setCourts([]);
      }
    } catch (err) {
      console.error('Failed to load courts:', err);
      setCourts([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    fetchCourts();
  };

  const formatPrice = (price) => {
    return price ? price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '0';
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

  const changeDate = (days) => {
    const currentDate = new Date(selectedDate);
    currentDate.setDate(currentDate.getDate() + days);
    
    // Don't allow dates before today
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    if (currentDate >= today) {
      const newDate = currentDate.toISOString().split('T')[0];
      setSelectedDate(newDate);
      
      // Clear selected slots that are now in the past
      const validSlots = selectedTimeSlots.filter(slot => {
        // Temporarily set date to check if slot is valid
        const tempDate = selectedDate;
        const isValid = !isSlotInPast(slot);
        return isValid;
      });
      
      if (validSlots.length !== selectedTimeSlots.length) {
        setSelectedTimeSlots(validSlots);
      }
    }
  };

  const handleDateChange = (e) => {
    const newDate = e.target.value;
    setSelectedDate(newDate);
    setShowDatePicker(false);
    
    // Clear selected slots that are now in the past
    const validSlots = selectedTimeSlots.filter(slot => {
      // Check if slot would be in past for new date
      const today = getTodayDate();
      if (newDate !== today) {
        return true; // Future dates, all slots valid
      }
      return !isSlotInPast(slot);
    });
    
    if (validSlots.length !== selectedTimeSlots.length) {
      setSelectedTimeSlots(validSlots);
    }
  };

  const toggleTimeSlot = (slot) => {
    const slotKey = `${slot.value}-${slot.period}`;
    const exists = selectedTimeSlots.find(s => `${s.value}-${s.period}` === slotKey);
    
    if (exists) {
      setSelectedTimeSlots(selectedTimeSlots.filter(s => `${s.value}-${s.period}` !== slotKey));
    } else {
      setSelectedTimeSlots([...selectedTimeSlots, slot]);
    }
  };

  const clearTimeSlots = () => {
    setSelectedTimeSlots([]);
  };

  const getFilteredTimeSlots = () => {
    let slots = timeSlots;
    
    // Filter by AM/PM if selected
    if (selectedPeriod !== 'all') {
      slots = slots.filter(slot => slot.period === selectedPeriod);
    }
    
    // Filter out past slots if today is selected
    slots = slots.filter(slot => !isSlotInPast(slot));
    
    return slots;
  };

  const getTimeSlotDisplay = () => {
    if (selectedTimeSlots.length === 0) return 'Any Time';
    if (selectedTimeSlots.length === 1) {
      const slot = selectedTimeSlots[0];
      return `${slot.label} ${slot.period.toUpperCase()}`;
    }
    return `${selectedTimeSlots.length} slots selected`;
  };

  return (
    <UserLayout>
      <div className="user-dashboard">
        {/* Hero Search Section */}
        <div className="search-hero">
          <div className="search-hero-content">
            <h1 className="search-title">Find Your Perfect Court</h1>
            <p className="search-subtitle">Book premium indoor sports venues across your city</p>
            
            <form onSubmit={handleSearch} className="search-form">
              <div className="search-filters-grid">
                {/* Court Name Filter */}
                <div className="filter-group">
                  <label className="filter-label">Court Name</label>
                  <input
                    type="text"
                    placeholder="Search by name..."
                    value={courtName}
                    onChange={(e) => setCourtName(e.target.value)}
                    className="filter-input-text"
                  />
                </div>

                {/* Address Filter */}
                <div className="filter-group">
                  <label className="filter-label">Address</label>
                  <input
                    type="text"
                    placeholder="Search by location..."
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    className="filter-input-text"
                  />
                </div>

                {/* Date Filter */}
                <div className="filter-group" ref={dateFilterRef}>
                  <label className="filter-label">Date</label>
                  <div className="filter-item date-filter">
                    <button
                      type="button"
                      onClick={() => changeDate(-1)}
                      className="date-nav-btn"
                      title="Previous day"
                    >
                      ‹
                    </button>
                    <div className="date-display">
                      {formatDate(selectedDate)}
                    </div>
                    <button
                      type="button"
                      onClick={() => changeDate(1)}
                      className="date-nav-btn"
                      title="Next day"
                    >
                      ›
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowDatePicker(!showDatePicker);
                      }}
                      className="calendar-btn"
                      title="Open calendar"
                    >
                      📅
                    </button>
                    {showDatePicker && (
                      <div className="date-picker-dropdown">
                        <input
                          type="date"
                          value={selectedDate}
                          onChange={handleDateChange}
                          min={getTodayDate()}
                          className="date-picker-input"
                        />
                      </div>
                    )}
                  </div>
                </div>

                {/* Time Slot Filter */}
                <div className="filter-group" ref={timeFilterRef}>
                  <label className="filter-label">Time Slots</label>
                  <div className="filter-item time-filter">
                    <div 
                      className="time-display"
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowTimeSlotPicker(!showTimeSlotPicker);
                      }}
                    >
                      {getTimeSlotDisplay()}
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowTimeSlotPicker(!showTimeSlotPicker);
                      }}
                      className="dropdown-btn"
                      title="Select time slots"
                    >
                      ▼
                    </button>
                  </div>
                  {showTimeSlotPicker && (
                    <div className="time-slot-dropdown">
                      <div className="time-slot-header">
                        <div className="period-tabs">
                          <button
                            type="button"
                            onClick={() => setSelectedPeriod('all')}
                            className={`period-tab ${selectedPeriod === 'all' ? 'active' : ''}`}
                          >
                            All Day
                          </button>
                          <button
                            type="button"
                            onClick={() => setSelectedPeriod('am')}
                            className={`period-tab ${selectedPeriod === 'am' ? 'active' : ''}`}
                          >
                            AM
                          </button>
                          <button
                            type="button"
                            onClick={() => setSelectedPeriod('pm')}
                            className={`period-tab ${selectedPeriod === 'pm' ? 'active' : ''}`}
                          >
                            PM
                          </button>
                        </div>
                        {selectedTimeSlots.length > 0 && (
                          <button
                            type="button"
                            onClick={clearTimeSlots}
                            className="clear-btn"
                          >
                            Clear All
                          </button>
                        )}
                      </div>
                      <div className="time-slots-grid">
                        {getFilteredTimeSlots().map((slot, index) => {
                          const isSelected = selectedTimeSlots.some(
                            s => s.value === slot.value && s.period === slot.period
                          );
                          const isPast = isSlotInPast(slot);
                          
                          return (
                            <button
                              key={`${slot.value}-${slot.period}-${index}`}
                              type="button"
                              onClick={() => !isPast && toggleTimeSlot(slot)}
                              className={`time-slot-btn ${isSelected ? 'selected' : ''} ${isPast ? 'disabled' : ''}`}
                              disabled={isPast}
                              title={isPast ? 'This time slot has passed' : ''}
                            >
                              {slot.label} {slot.period.toUpperCase()}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <button type="submit" className="search-btn" disabled={loading}>
                {loading ? 'Searching...' : 'Search Courts'}
              </button>
            </form>
          </div>
        </div>

        {/* Results Section */}
        <div className="search-results">
          <div className="results-header">
            <h2 className="results-title">Available Courts</h2>
            {courts.length > 0 && (
              <span className="results-count">{courts.length} courts</span>
            )}
          </div>

          {loading ? (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>Finding courts for you...</p>
            </div>
          ) : courts.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">🏟️</div>
              <h3>No courts found</h3>
              <p>Try adjusting your search filters or check back later</p>
            </div>
          ) : (
            <div className="courts-grid">
              {courts.map((court) => (
                <div key={court.id} className="court-card" onClick={() => navigate(`/courts/${court.id}`)}>
                  <div className="court-image" data-sport={court.sport_type}>
                    {court.media && court.media.length > 0 ? (
                      <img 
                        src={court.media[0].url} 
                        alt={court.name}
                        onError={(e) => {
                          e.target.src = 'https://via.placeholder.com/400x250?text=Court+Image';
                        }}
                      />
                    ) : (
                      <div className="court-image-placeholder">
                        <span>🏟️</span>
                      </div>
                    )}
                    <div className="court-badge">{court.sport_type}</div>
                  </div>
                  
                  <div className="court-content">
                    <h3 className="court-name">{court.name}</h3>
                    <p className="court-location">
                      📍 {court.property?.address || 'Location not specified'}
                    </p>
                    
                    <div className="court-footer">
                      <div className="court-price">
                        <span className="price-value">
                          Rs {formatPrice(court.base_price)}<span>/hr</span>
                        </span>
                      </div>
                      
                      <div className="court-rating">
                        ★ 4.8
                      </div>
                    </div>
                    
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/courts/${court.id}/book`);
                      }}
                      className="btn-book"
                    >
                      Book Now
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </UserLayout>
  );
};

export default UserDashboard;

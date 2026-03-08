import React from 'react';
import './pricingCard.css';

const DAYS_MAP = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const DAYS_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const PricingCard = ({ pricing, pricingNumber, onEdit, onDelete }) => {
  // Calculate time coverage percentage
  const calculateCoverage = () => {
    const [startHour, startMin] = pricing.start_time.split(':').map(Number);
    const [endHour, endMin] = pricing.end_time.split(':').map(Number);
    
    const startMinutes = startHour * 60 + startMin;
    const endMinutes = endHour * 60 + endMin;
    
    const duration = endMinutes - startMinutes;
    const percentage = (duration / 1440) * 100; // 1440 minutes in a day
    
    return {
      percentage: Math.min(100, Math.max(0, percentage)),
      hours: Math.floor(duration / 60),
      isAllDay: duration >= 1440 || duration >= 1380 // 23+ hours
    };
  };

  const coverage = calculateCoverage();

  // Format price with comma
  const formatPrice = (price) => {
    return price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  };

  // Format time for display (remove seconds)
  const formatTime = (time) => {
    return time.substring(0, 5); // "07:00:00" -> "07:00"
  };

  // Convert day numbers to day names
  const getDayNames = () => {
    if (!pricing.days || pricing.days.length === 0) return [];
    
    // Check if days are already strings (day names) or numbers
    if (typeof pricing.days[0] === 'string' && pricing.days[0].length > 2) {
      // Already day names, return as is
      return pricing.days;
    }
    
    // Convert numbers to short day names
    return pricing.days.map(day => DAYS_SHORT[day]);
  };

  const dayNames = getDayNames();

  return (
    <div className="ch-pricing-card">
      {/* Left accent strip */}
      <div className="ch-pricing-accent"></div>

      {/* Card body */}
      <div className="ch-pricing-body">
        {/* Meta section */}
        <div className="ch-pricing-meta">
          <div className="ch-pricing-rule-label">
            ⚡ PRICING RULE #{pricingNumber}
            {pricing.label && <span className="ch-pricing-label-text"> • {pricing.label}</span>}
          </div>
          
          <div className="ch-pricing-days-row">
            {dayNames.map((day, idx) => (
              <span key={idx} className="ch-pricing-day-pill">
                {day}
              </span>
            ))}
          </div>

          <div className="ch-pricing-time-row">
            <span className="ch-pricing-time-icon">🕐</span>
            <span className="ch-pricing-time-range">
              {formatTime(pricing.start_time)} – {formatTime(pricing.end_time)}
            </span>
            <span className="ch-pricing-duration">
              {coverage.isAllDay ? '(All day)' : `(${coverage.hours} hrs)`}
            </span>
          </div>
        </div>

        {/* Time bar visualization */}
        <div className="ch-pricing-timebar">
          <div className="ch-pricing-timebar-label">DAY COVERAGE</div>
          <div className="ch-pricing-timebar-track">
            <div 
              className="ch-pricing-timebar-fill" 
              style={{ width: `${coverage.percentage}%` }}
            ></div>
          </div>
        </div>

        {/* Price section */}
        <div className="ch-pricing-price-section">
          <div className="ch-pricing-amount">PKR {formatPrice(pricing.price_per_hour)}</div>
          <div className="ch-pricing-unit">/hr</div>
        </div>
      </div>

      {/* Card actions */}
      <div className="ch-pricing-actions">
        <button 
          className="ch-pricing-btn-edit"
          onClick={() => onEdit(pricing)}
        >
          ✏️ Edit
        </button>
        <button 
          className="ch-pricing-btn-delete"
          onClick={() => onDelete(pricing.id)}
        >
          🗑 Delete
        </button>
      </div>
    </div>
  );
};

export default PricingCard;

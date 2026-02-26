import React, { useState, useEffect } from 'react';
import './pricingModal.css';

const DAYS = [
  { value: 0, label: 'Mon' },
  { value: 1, label: 'Tue' },
  { value: 2, label: 'Wed' },
  { value: 3, label: 'Thu' },
  { value: 4, label: 'Fri' },
  { value: 5, label: 'Sat' },
  { value: 6, label: 'Sun' }
];

const PricingModal = ({ isOpen, onClose, onSubmit, initialData = null }) => {
  const [formData, setFormData] = useState({
    days: [],
    start_time: '09:00',
    end_time: '17:00',
    price_per_hour: '',
    label: ''
  });
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (initialData) {
      setFormData({
        days: initialData.days || [],
        start_time: initialData.start_time || '09:00',
        end_time: initialData.end_time || '17:00',
        price_per_hour: initialData.price_per_hour || '',
        label: initialData.label || ''
      });
    } else {
      setFormData({
        days: [],
        start_time: '09:00',
        end_time: '17:00',
        price_per_hour: '',
        label: ''
      });
    }
    setErrors({});
  }, [initialData, isOpen]);

  const handleDayToggle = (dayValue) => {
    setFormData(prev => ({
      ...prev,
      days: prev.days.includes(dayValue)
        ? prev.days.filter(d => d !== dayValue)
        : [...prev.days, dayValue].sort((a, b) => a - b)
    }));
  };

  const validate = () => {
    const newErrors = {};
    
    if (formData.days.length === 0) {
      newErrors.days = 'Select at least one day';
    }
    
    if (!formData.price_per_hour || formData.price_per_hour <= 0) {
      newErrors.price_per_hour = 'Price must be greater than 0';
    }
    
    if (formData.start_time >= formData.end_time) {
      newErrors.time = 'End time must be after start time';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validate()) {
      onSubmit({
        ...formData,
        price_per_hour: parseFloat(formData.price_per_hour)
      });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="pricing-modal-overlay" onClick={onClose}>
      <div className="pricing-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="pricing-modal-header">
          <h2>{initialData ? 'Edit Pricing Rule' : 'Add Pricing Rule'}</h2>
          <button className="pricing-modal-close" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="pricing-modal-form">
          <div className="pricing-form-group">
            <label>Days *</label>
            <div className="pricing-days-selector">
              {DAYS.map(day => (
                <button
                  key={day.value}
                  type="button"
                  className={`pricing-day-btn ${formData.days.includes(day.value) ? 'active' : ''}`}
                  onClick={() => handleDayToggle(day.value)}
                >
                  {day.label}
                </button>
              ))}
            </div>
            {errors.days && <span className="pricing-error">{errors.days}</span>}
          </div>

          <div className="pricing-form-row">
            <div className="pricing-form-group">
              <label htmlFor="start_time">Start Time *</label>
              <input
                type="time"
                id="start_time"
                value={formData.start_time}
                onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                required
              />
            </div>

            <div className="pricing-form-group">
              <label htmlFor="end_time">End Time *</label>
              <input
                type="time"
                id="end_time"
                value={formData.end_time}
                onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                required
              />
            </div>
          </div>
          {errors.time && <span className="pricing-error">{errors.time}</span>}

          <div className="pricing-form-group">
            <label htmlFor="price_per_hour">Price per Hour ($) *</label>
            <input
              type="number"
              id="price_per_hour"
              step="0.01"
              min="0"
              value={formData.price_per_hour}
              onChange={(e) => setFormData({ ...formData, price_per_hour: e.target.value })}
              placeholder="e.g., 50.00"
              required
            />
            {errors.price_per_hour && <span className="pricing-error">{errors.price_per_hour}</span>}
          </div>

          <div className="pricing-form-group">
            <label htmlFor="label">Label (Optional)</label>
            <input
              type="text"
              id="label"
              maxLength="100"
              value={formData.label}
              onChange={(e) => setFormData({ ...formData, label: e.target.value })}
              placeholder="e.g., Peak Hours, Weekend Rate"
            />
          </div>

          <div className="pricing-modal-actions">
            <button type="button" className="pricing-btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="pricing-btn-primary">
              {initialData ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default PricingModal;

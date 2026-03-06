import React, { useState, useEffect } from 'react';
import './pricingModal.css';

const DAYS = [
  { value: 0, label: 'Monday', short: 'Mon' },
  { value: 1, label: 'Tuesday', short: 'Tue' },
  { value: 2, label: 'Wednesday', short: 'Wed' },
  { value: 3, label: 'Thursday', short: 'Thu' },
  { value: 4, label: 'Friday', short: 'Fri' },
  { value: 5, label: 'Saturday', short: 'Sat' },
  { value: 6, label: 'Sunday', short: 'Sun' }
];

// Generate 24 hour slots (0-23)
const TIME_SLOTS = Array.from({ length: 24 }, (_, i) => {
  const hour = i;
  const nextHour = i + 1;
  
  const formatHour = (h) => {
    if (h === 0) return '12 AM';
    if (h === 12) return '12 PM';
    if (h === 24) return '12 AM'; // For display of next day midnight
    if (h < 12) return `${h} AM`;
    return `${h - 12} PM`;
  };
  
  return {
    value: hour,
    label: `${formatHour(hour)} - ${formatHour(nextHour)}`,
    start: `${String(hour).padStart(2, '0')}:00`,
    // For the last slot (23), end time should be 23:59 instead of 24:00
    end: nextHour === 24 ? '23:59' : `${String(nextHour).padStart(2, '0')}:00`
  };
});

const PricingModal = ({ isOpen, onClose, onSubmit, initialData = null }) => {
  const [selectedSlots, setSelectedSlots] = useState([]);
  const [selectedDays, setSelectedDays] = useState([]);
  const [price, setPrice] = useState('');
  const [label, setLabel] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [dragStartSlot, setDragStartSlot] = useState(null);
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (initialData) {
      // If editing, convert time range to slots
      const startHour = parseInt(initialData.start_time?.split(':')[0] || 0);
      const endHour = parseInt(initialData.end_time?.split(':')[0] || 0);
      const slots = [];
      for (let i = startHour; i < endHour; i++) {
        slots.push(i);
      }
      setSelectedSlots(slots);
      setSelectedDays(initialData.days || []);
      setPrice(initialData.price_per_hour || '');
      setLabel(initialData.label || '');
    } else {
      resetForm();
    }
    setErrors({});
  }, [initialData, isOpen]);

  const resetForm = () => {
    setSelectedSlots([]);
    setSelectedDays([]);
    setPrice('');
    setLabel('');
    setErrors({});
    setIsSubmitting(false);
  };

  const handleSlotMouseDown = (slotValue) => {
    setIsDragging(true);
    setDragStartSlot(slotValue);
    
    // Toggle the slot on mouse down
    setSelectedSlots(prev => 
      prev.includes(slotValue)
        ? prev.filter(s => s !== slotValue)
        : [...prev, slotValue].sort((a, b) => a - b)
    );
  };

  const handleSlotMouseEnter = (slotValue) => {
    if (isDragging && dragStartSlot !== null) {
      // Add slot if not already selected during drag
      if (!selectedSlots.includes(slotValue)) {
        setSelectedSlots(prev => [...prev, slotValue].sort((a, b) => a - b));
      }
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setDragStartSlot(null);
  };

  const handleDayToggle = (dayValue) => {
    setSelectedDays(prev =>
      prev.includes(dayValue)
        ? prev.filter(d => d !== dayValue)
        : [...prev, dayValue].sort((a, b) => a - b)
    );
  };

  const selectAllDays = () => {
    setSelectedDays(DAYS.map(d => d.value));
  };

  const selectWeekdays = () => {
    setSelectedDays([0, 1, 2, 3, 4]); // Mon-Fri
  };

  const selectWeekends = () => {
    setSelectedDays([5, 6]); // Sat-Sun
  };

  const clearDays = () => {
    setSelectedDays([]);
  };

  const validate = () => {
    const newErrors = {};
    
    if (selectedSlots.length === 0) {
      newErrors.slots = 'Select at least one time slot';
    }
    
    if (selectedDays.length === 0) {
      newErrors.days = 'Select at least one day';
    }
    
    if (!price || parseFloat(price) <= 0) {
      newErrors.price = 'Price must be greater than 0';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validate() && !isSubmitting) {
      setIsSubmitting(true);
      
      // Smart grouping algorithm with circular time support
      const sortedSlots = [...selectedSlots].sort((a, b) => a - b);
      
      // Find consecutive groups (including circular wrap-around)
      const findConsecutiveGroups = (slots) => {
        if (slots.length === 0) return [];
        if (slots.length === 1) return [[slots[0]]];
        
        const groups = [];
        let currentGroup = [slots[0]];
        
        for (let i = 1; i < slots.length; i++) {
          if (slots[i] === slots[i - 1] + 1) {
            // Consecutive slot
            currentGroup.push(slots[i]);
          } else {
            // Gap found, save current group and start new one
            groups.push(currentGroup);
            currentGroup = [slots[i]];
          }
        }
        groups.push(currentGroup);
        
        // Check for circular wrap-around (last group connects to first group)
        // This happens when we have slots at the end (e.g., 22, 23) and beginning (e.g., 0, 1)
        if (groups.length > 1) {
          const firstGroup = groups[0];
          const lastGroup = groups[groups.length - 1];
          
          // Check if last slot is 23 and first slot is 0 (wraps around midnight)
          if (lastGroup[lastGroup.length - 1] === 23 && firstGroup[0] === 0) {
            // Check if they're actually consecutive through midnight
            let isCircular = true;
            
            // Verify last group ends at 23
            if (lastGroup[lastGroup.length - 1] !== 23) {
              isCircular = false;
            }
            
            // Verify first group starts at 0 and is consecutive
            for (let i = 1; i < firstGroup.length; i++) {
              if (firstGroup[i] !== firstGroup[i - 1] + 1) {
                isCircular = false;
                break;
              }
            }
            
            if (isCircular) {
              // Merge: last group + first group (circular)
              const mergedGroup = [...lastGroup, ...firstGroup];
              // Remove first and last groups, add merged group
              groups.shift(); // Remove first group
              groups.pop();   // Remove last group
              groups.push(mergedGroup); // Add merged circular group
            }
          }
        }
        
        return groups;
      };
      
      const slotGroups = findConsecutiveGroups(sortedSlots);
      
      // Create pricing rules for each group
      const pricingRules = [];
      
      slotGroups.forEach(group => {
        const startSlot = group[0];
        const endSlot = group[group.length - 1];
        
        // Handle circular time (when group wraps around midnight)
        const hasWrapAround = group.includes(23) && group.includes(0);
        
        if (hasWrapAround) {
          // Split into two rules at midnight to satisfy backend validation (end_time > start_time)
          const beforeMidnight = group.filter(s => s >= 12);
          const afterMidnight = group.filter(s => s < 12);
          
          // Rule 1: Before midnight (e.g., 5 PM - 11:59 PM)
          if (beforeMidnight.length > 0) {
            const rule1 = {
              days: selectedDays,
              start_time: TIME_SLOTS[Math.min(...beforeMidnight)].start,
              end_time: '23:59', // End at 11:59 PM
              price_per_hour: parseFloat(price)
            };
            if (label && label.trim()) {
              rule1.label = label.trim();
            }
            pricingRules.push(rule1);
          }
          
          // Rule 2: After midnight (e.g., 12 AM - 7 AM)
          if (afterMidnight.length > 0) {
            const lastSlot = Math.max(...afterMidnight);
            const rule2 = {
              days: selectedDays,
              start_time: '00:00', // Start at midnight
              end_time: TIME_SLOTS[lastSlot].end,
              price_per_hour: parseFloat(price)
            };
            if (label && label.trim()) {
              rule2.label = label.trim();
            }
            pricingRules.push(rule2);
          }
        } else {
          // Normal consecutive group (no wrap-around)
          const rule = {
            days: selectedDays,
            start_time: TIME_SLOTS[startSlot].start,
            end_time: TIME_SLOTS[endSlot].end,
            price_per_hour: parseFloat(price)
          };
          if (label && label.trim()) {
            rule.label = label.trim();
          }
          pricingRules.push(rule);
        }
      });
      
      console.log('Selected slots:', sortedSlots);
      console.log('Grouped into:', slotGroups);
      console.log('Submitting pricing rules:', pricingRules);
      
      // If editing, send single rule (first group only)
      // If creating, send all rules
      if (initialData) {
        onSubmit(pricingRules[0]);
      } else {
        // Send multiple rules
        onSubmit({ rules: pricingRules, multiple: true });
      }
    }
  };


  if (!isOpen) return null;

  return (
    <div className="pricing-modal-overlay" onClick={onClose}>
      <div 
        className="pricing-modal-content pricing-modal-large" 
        onClick={(e) => e.stopPropagation()}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <div className="pricing-modal-header">
          <h2>{initialData ? 'Edit Pricing Rule' : 'Add Pricing Rule'}</h2>
          <button className="pricing-modal-close" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="pricing-modal-form">
          {/* Time Slots Section */}
          <div className="pricing-form-section">
            <div className="pricing-section-header">
              <label>Select Time Slots *</label>
              <span className="pricing-helper-text">
                Click or drag to select hours • {selectedSlots.length} slot{selectedSlots.length !== 1 ? 's' : ''} selected
              </span>
            </div>
            
            <div className="pricing-slots-grid">
              {TIME_SLOTS.map(slot => (
                <div
                  key={slot.value}
                  className={`pricing-slot ${selectedSlots.includes(slot.value) ? 'selected' : ''}`}
                  onMouseDown={() => handleSlotMouseDown(slot.value)}
                  onMouseEnter={() => handleSlotMouseEnter(slot.value)}
                >
                  <span className="pricing-slot-time">{slot.label}</span>
                </div>
              ))}
            </div>
            {errors.slots && <span className="pricing-error">{errors.slots}</span>}
          </div>

          {/* Days Section */}
          <div className="pricing-form-section">
            <div className="pricing-section-header">
              <label>Select Days *</label>
              <div className="pricing-quick-select">
                <button type="button" className="pricing-quick-btn" onClick={selectAllDays}>All</button>
                <button type="button" className="pricing-quick-btn" onClick={selectWeekdays}>Weekdays</button>
                <button type="button" className="pricing-quick-btn" onClick={selectWeekends}>Weekends</button>
                <button type="button" className="pricing-quick-btn" onClick={clearDays}>Clear</button>
              </div>
            </div>
            
            <div className="pricing-days-grid">
              {DAYS.map(day => (
                <button
                  key={day.value}
                  type="button"
                  className={`pricing-day-card ${selectedDays.includes(day.value) ? 'selected' : ''}`}
                  onClick={() => handleDayToggle(day.value)}
                >
                  <span className="pricing-day-short">{day.short}</span>
                  <span className="pricing-day-full">{day.label}</span>
                </button>
              ))}
            </div>
            {errors.days && <span className="pricing-error">{errors.days}</span>}
          </div>

          {/* Price and Label Section */}
          <div className="pricing-form-row">
            <div className="pricing-form-group">
              <label htmlFor="price">Price per Hour (PKR) *</label>
              <input
                type="number"
                id="price"
                step="0.01"
                min="0"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                placeholder="e.g., 50.00"
                required
              />
              {errors.price && <span className="pricing-error">{errors.price}</span>}
            </div>

            <div className="pricing-form-group">
              <label htmlFor="label">Label (Optional)</label>
              <input
                type="text"
                id="label"
                maxLength="100"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder="e.g., Peak Hours, Weekend Rate"
              />
            </div>
          </div>

          {/* Summary */}
          {selectedSlots.length > 0 && selectedDays.length > 0 && price && (
            <div className="pricing-summary">
              <div className="pricing-summary-icon">📊</div>
              <div className="pricing-summary-text">
                <strong>Summary:</strong> {(() => {
                  // Calculate consecutive groups (same logic as handleSubmit)
                  const sortedSlots = [...selectedSlots].sort((a, b) => a - b);
                  let groups = 1;
                  
                  for (let i = 1; i < sortedSlots.length; i++) {
                    if (sortedSlots[i] !== sortedSlots[i - 1] + 1) {
                      groups++;
                    }
                  }
                  
                  // Check for circular wrap-around
                  if (groups > 1 && sortedSlots.includes(23) && sortedSlots.includes(0)) {
                    // Check if they connect through midnight
                    const hasGapAtMidnight = sortedSlots[sortedSlots.length - 1] === 23 && sortedSlots[0] === 0;
                    if (hasGapAtMidnight) {
                      groups--; // They merge into one circular group
                    }
                  }
                  
                  const totalRules = groups * selectedDays.length;
                  return `Creating ${groups} time range${groups !== 1 ? 's' : ''} × ${selectedDays.length} day${selectedDays.length !== 1 ? 's' : ''} = ${totalRules} pricing rule${totalRules !== 1 ? 's' : ''} at PKR ${price}/hour`;
                })()}
              </div>
            </div>
          )}

          <div className="pricing-modal-actions">
            <button type="button" className="pricing-btn-secondary" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </button>
            <button type="submit" className="pricing-btn-primary" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <span className="pricing-btn-spinner"></span>
                  {initialData ? 'Updating...' : 'Creating...'}
                </>
              ) : (
                <>{initialData ? 'Update' : 'Create'} Pricing Rule</>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default PricingModal;

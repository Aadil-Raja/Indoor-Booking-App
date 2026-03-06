# Test Data Setup for Chatbot Integration

## Required Data in Management Database

To test the chatbot, you need the following data in your management database:

### 1. Users Table
```sql
-- Owner user (the property owner)
INSERT INTO users (id, email, password_hash, role, is_active, is_verified)
VALUES (
  'owner-uuid-1',
  'owner@example.com',
  'hashed_password',
  'owner',
  true,
  true
);

-- Customer user (the person booking)
INSERT INTO users (id, email, password_hash, role, is_active, is_verified)
VALUES (
  'customer-uuid-1',
  'customer@example.com',
  'hashed_password',
  'customer',
  true,
  true
);
```

### 2. Owner Profiles Table
```sql
-- Owner profile linked to owner user
INSERT INTO owner_profiles (id, user_id, business_name, phone, address)
VALUES (
  'owner-profile-uuid-1',
  'owner-uuid-1',
  'Downtown Sports Center',
  '+1234567890',
  '123 Main St, City'
);
```

### 3. Properties Table
```sql
-- Property linked to owner_profile
INSERT INTO properties (id, owner_profile_id, name, description, address, city, state, zip_code, country)
VALUES (
  'property-uuid-1',
  'owner-profile-uuid-1',
  'Downtown Sports Complex',
  'Modern indoor sports facility with multiple courts',
  '123 Main St',
  'New York',
  'NY',
  '10001',
  'USA'
);
```

### 4. Courts Table
```sql
-- Tennis court
INSERT INTO courts (id, property_id, name, sport_type, description, hourly_rate)
VALUES (
  'court-uuid-1',
  'property-uuid-1',
  'Tennis Court A',
  'tennis',
  'Professional tennis court with lighting',
  50.00
);

-- Basketball court
INSERT INTO courts (id, property_id, name, sport_type, description, hourly_rate)
VALUES (
  'court-uuid-2',
  'property-uuid-1',
  'Basketball Court 1',
  'basketball',
  'Full-size indoor basketball court',
  75.00
);
```

### 5. Pricing Rules (Optional)
```sql
-- Peak hour pricing for tennis court
INSERT INTO pricing_rules (id, court_id, day_of_week, start_time, end_time, price_per_hour)
VALUES (
  'pricing-uuid-1',
  'court-uuid-1',
  NULL,  -- All days
  '18:00:00',
  '22:00:00',
  75.00  -- Peak hour rate
);
```

### 6. Availability/Blocked Slots (Optional)
```sql
-- Block a specific time slot
INSERT INTO blocked_slots (id, court_id, blocked_date, start_time, end_time, reason)
VALUES (
  'blocked-uuid-1',
  'court-uuid-1',
  '2024-01-15',
  '14:00:00',
  '16:00:00',
  'Maintenance'
);
```

## Quick Setup Script

You can use the existing signup/login flow to create users, or run this SQL:

```sql
-- Complete test data setup
BEGIN;

-- 1. Create owner user
INSERT INTO users (email, password_hash, role, is_active, is_verified)
VALUES ('owner@test.com', '$2b$12$...', 'owner', true, true)
RETURNING id;  -- Note this ID

-- 2. Create customer user
INSERT INTO users (email, password_hash, role, is_active, is_verified)
VALUES ('customer@test.com', '$2b$12$...', 'customer', true, true)
RETURNING id;  -- Note this ID

-- 3. Create owner profile (use owner user ID from step 1)
INSERT INTO owner_profiles (user_id, business_name, phone, address)
VALUES ('owner-user-id', 'Test Sports Center', '1234567890', '123 Test St')
RETURNING id;  -- Note this ID

-- 4. Create property (use owner_profile ID from step 3)
INSERT INTO properties (owner_profile_id, name, description, address, city, state, zip_code, country)
VALUES (
  'owner-profile-id',
  'Test Sports Complex',
  'Test facility',
  '123 Test St',
  'Test City',
  'TS',
  '12345',
  'USA'
)
RETURNING id;  -- Note this ID

-- 5. Create courts (use property ID from step 4)
INSERT INTO courts (property_id, name, sport_type, description, hourly_rate)
VALUES 
  ('property-id', 'Tennis Court A', 'tennis', 'Test tennis court', 50.00),
  ('property-id', 'Basketball Court 1', 'basketball', 'Test basketball court', 75.00);

COMMIT;
```

## Using Existing Frontend Data

If you already have data from the owner portal:
1. Use an existing owner account
2. Make sure they have at least one property
3. Make sure the property has at least one court
4. The chatbot will work with this existing data

## Important Notes

- **owner_id in chatbot**: This refers to the `user_id` of the owner (not owner_profile_id)
- Properties are linked to `owner_profiles`, which are linked to `users`
- The chatbot tools will navigate: user → owner_profile → properties → courts

# Chatbot Testing Guide

This guide explains how to test the WhatsApp-style chatbot integration.

## Prerequisites

### 1. Database Setup

You need TWO databases running:

**Management Database (Sync)**:
- Contains: users, owner_profiles, properties, courts, bookings, etc.
- Port: 5432 (default PostgreSQL)
- Configured in: `Backend/apps/management/.env`

**Chatbot Database (Async)**:
- Contains: chats, messages
- Port: 5433 (or different from management)
- Configured in: `Backend/apps/chatbot/.env`

### 2. Environment Configuration

**Backend/apps/management/.env**:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/management_db
JWT_SECRET=your-secret-key
```

**Backend/apps/chatbot/.env**:
```env
# Chatbot's own async database
CHAT_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5433/chatbot_db

# Main database for reading properties/courts (sync)
MAIN_DATABASE_URL=postgresql://user:password@localhost:5432/management_db

# LLM Provider
OPENAI_API_KEY=your-openai-api-key
LLM_PROVIDER=openai

# Session settings
SESSION_EXPIRY_HOURS=24
```

### 3. Run Migrations

```bash
# Management database migrations
cd Backend
alembic upgrade head

# Chatbot database migrations
cd Backend/apps/chatbot
alembic upgrade head
```

## Step-by-Step Testing

### Step 1: Create Test Data

#### Option A: Use Existing Owner Portal Data

If you already have data from the owner portal:
1. You have at least one owner user
2. Owner has completed their profile
3. Owner has created at least one property
4. Property has at least one court

Skip to Step 2.

#### Option B: Create Fresh Test Data

1. **Start the management API**:
```bash
cd Backend/apps/management
uvicorn app.main:app --reload --port 8000
```

2. **Start the frontend**:
```bash
cd Frontend
npm run dev
```

3. **Create Owner Account**:
   - Go to http://localhost:5173/auth
   - Click "Sign Up"
   - Fill in:
     - Email: owner@test.com
     - Password: Test123!
     - Role: Owner
   - Click "Sign Up"

4. **Complete Owner Profile**:
   - After signup, you'll be redirected to dashboard
   - Go to "Profile" in sidebar
   - Fill in:
     - Business Name: Test Sports Center
     - Phone: 1234567890
     - Address: 123 Test St
   - Click "Save Profile"

5. **Create Property**:
   - Go to "Properties" in sidebar
   - Click "Add New Property"
   - Fill in:
     - Name: Downtown Sports Complex
     - Description: Modern indoor facility
     - Address: 123 Main St
     - City: New York
     - State: NY
     - Zip: 10001
     - Country: USA
   - Click "Create Property"

6. **Add Courts**:
   - Click on the property you just created
   - Click "Add Court"
   - Fill in:
     - Name: Tennis Court A
     - Sport Type: tennis
     - Description: Professional court
     - Hourly Rate: 50
   - Click "Create Court"
   - Repeat for more courts (basketball, badminton, etc.)

7. **Create Customer Account**:
   - Logout (top right)
   - Click "Sign Up" again
   - Fill in:
     - Email: customer@test.com
     - Password: Test123!
     - Role: Customer
   - Click "Sign Up"

### Step 2: Get User IDs

Run the helper script to get the IDs you need:

```bash
cd Backend
python scripts/get_test_ids.py
```

This will display:
- All users with their IDs
- All properties with owner IDs
- All courts with details

**Copy these IDs**:
- Customer User ID (for testing as customer)
- Owner User ID (the property owner)

### Step 3: Start Chatbot API

```bash
cd Backend/apps/chatbot
uvicorn app.main:app --reload --port 8001
```

Verify it's running:
- Go to http://localhost:8001/api/health
- Should return: `{"status": "healthy"}`

### Step 4: Test the Chatbot

1. **Open Chatbot Test Interface**:
   - Go to http://localhost:5173/chatbot-test

2. **Configure Chat**:
   - Paste **Customer User ID** in "User ID (Customer)" field
   - Paste **Owner User ID** in "Owner ID" field
   - Click "Start Chat"

3. **Test Conversation Flow**:

   **Test 1: Greeting**
   ```
   You: Hello
   Bot: Hello! I'm your sports booking assistant...
   ```

   **Test 2: Search**
   ```
   You: Show me available tennis courts
   Bot: Here are the available facilities:
   [List of properties with courts]
   ```

   **Test 3: Booking Flow**
   ```
   You: I want to book a tennis court
   Bot: Which facility would you like to book?
   [Buttons with property names]
   
   You: [Click property button]
   Bot: Which court would you like to book?
   [List of courts with prices]
   
   You: [Click court]
   Bot: What date would you like to book?
   
   You: Tomorrow
   Bot: What time would you like to book?
   [List of available time slots with prices]
   
   You: [Click time slot]
   Bot: Here's your booking summary:
        Property: Downtown Sports Complex
        Court: Tennis Court A
        Date: 2024-01-15
        Time: 14:00
        Price: $50.00
        
        Would you like to confirm this booking?
   
   You: Yes
   Bot: Great! Your booking has been confirmed.
        Booking ID: [booking-id]
   ```

   **Test 4: FAQ**
   ```
   You: What sports do you have?
   Bot: We offer various indoor sports including...
   ```

   **Test 5: Session Continuity**
   - Wait 5 minutes
   - Send another message
   - Bot should continue the conversation
   
   - Close browser
   - Reopen after 25+ hours
   - Send a message
   - Bot should ask: "Are you referring to our previous conversation?"

### Step 5: Verify Data

1. **Check Chat Database**:
```sql
-- Connect to chatbot database
psql -h localhost -p 5433 -U user -d chatbot_db

-- View chats
SELECT id, user_id, owner_id, status, last_message_at, flow_state 
FROM chats 
ORDER BY last_message_at DESC;

-- View messages
SELECT chat_id, sender_type, message_type, content, created_at 
FROM messages 
WHERE chat_id = 'your-chat-id'
ORDER BY created_at;
```

2. **Check Bookings in Management Database**:
```sql
-- Connect to management database
psql -h localhost -p 5432 -U user -d management_db

-- View bookings created by chatbot
SELECT id, user_id, court_id, booking_date, start_time, end_time, status
FROM bookings
ORDER BY created_at DESC;
```

## Understanding the Flow

### What the Chatbot Receives

When you send a message, the chatbot receives:
```json
{
  "user_id": "customer-uuid",  // The customer who wants to book
  "owner_id": "owner-uuid",    // The property owner (NOT owner_profile_id)
  "content": "I want to book a tennis court"
}
```

### How Owner ID Works

**Important**: The chatbot uses `owner_id` which is the **user ID** of the owner, NOT the `owner_profile_id`.

The relationship is:
```
User (owner_id)
  ↓
OwnerProfile (owner_profile_id)
  ↓
Properties
  ↓
Courts
```

The chatbot tools navigate this relationship automatically:
1. Receives `owner_id` (user ID)
2. Finds `owner_profile` linked to that user
3. Finds `properties` linked to that owner_profile
4. Finds `courts` linked to those properties

### Message Types

The chatbot can send different message types:

**Text**:
```json
{
  "message_type": "text",
  "content": "Hello! How can I help you?",
  "message_metadata": {}
}
```

**Buttons**:
```json
{
  "message_type": "button",
  "content": "Which facility would you like?",
  "message_metadata": {
    "buttons": [
      {"id": "prop-1", "text": "Downtown Sports Center"},
      {"id": "prop-2", "text": "Westside Arena"}
    ]
  }
}
```

**List**:
```json
{
  "message_type": "list",
  "content": "Available time slots:",
  "message_metadata": {
    "list_items": [
      {
        "id": "slot-1",
        "title": "2:00 PM",
        "description": "$50/hour"
      }
    ]
  }
}
```

## Troubleshooting

### Issue: "Chat database connection failed"

**Solution**:
- Check chatbot database is running on port 5433
- Verify `CHAT_DATABASE_URL` in `Backend/apps/chatbot/.env`
- Run chatbot migrations: `cd Backend/apps/chatbot && alembic upgrade head`

### Issue: "No properties found"

**Solution**:
- Verify owner has created properties via owner portal
- Check owner_id is correct (use `get_test_ids.py`)
- Verify properties are linked to owner_profile

### Issue: "LLM provider error"

**Solution**:
- Check `OPENAI_API_KEY` is set in `Backend/apps/chatbot/.env`
- Verify you have OpenAI API credits
- Check internet connection

### Issue: "Booking creation failed"

**Solution**:
- Verify court exists and is active
- Check date/time is in the future
- Verify no conflicting bookings
- Check booking_service is working

### Issue: "Session expired prompt not showing"

**Solution**:
- Check `SESSION_EXPIRY_HOURS` in config (default: 24)
- Verify `last_message_at` is being updated
- Check system time is correct

## API Endpoints

### Chatbot API (Port 8001)

```bash
# Send message
POST http://localhost:8001/api/chat/message
{
  "user_id": "uuid",
  "owner_id": "uuid",
  "content": "Hello"
}

# Get chat history
GET http://localhost:8001/api/chat/history/{chat_id}

# List user's chats
GET http://localhost:8001/api/chat/list?user_id={user_id}

# Create new chat
POST http://localhost:8001/api/chat/new
{
  "user_id": "uuid",
  "owner_id": "uuid"
}

# Health check
GET http://localhost:8001/api/health
```

## Next Steps

After successful testing:

1. **Build Production Chat UI**:
   - Create proper customer portal
   - Add chat list view
   - Add real-time updates (WebSocket)
   - Add file upload support

2. **Add Authentication**:
   - Integrate with existing auth system
   - Auto-populate user_id from token
   - Add owner selection UI

3. **Enhance Features**:
   - Add payment integration
   - Add booking confirmation emails
   - Add push notifications
   - Add chat history search

4. **Deploy**:
   - Set up production databases
   - Configure environment variables
   - Set up monitoring and logging
   - Add rate limiting

## Support

If you encounter issues:
1. Check logs in terminal where APIs are running
2. Check browser console for frontend errors
3. Verify all environment variables are set
4. Ensure all migrations are run
5. Check database connections

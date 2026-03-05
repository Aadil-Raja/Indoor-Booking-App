# Chatbot Quick Start

## TL;DR - Get Testing in 5 Minutes

### 1. Setup Databases (if not already done)

```bash
# Create chatbot database
createdb -p 5433 chatbot_db

# Run migrations
cd Backend/apps/chatbot
alembic upgrade head
```

### 2. Configure Environment

**Backend/apps/chatbot/.env**:
```env
CHAT_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5433/chatbot_db
MAIN_DATABASE_URL=postgresql://user:password@localhost:5432/management_db
OPENAI_API_KEY=your-key-here
```

### 3. Start Services

```bash
# Terminal 1: Management API
cd Backend/apps/management
uvicorn app.main:app --reload --port 8000

# Terminal 2: Chatbot API
cd Backend/apps/chatbot
uvicorn app.main:app --reload --port 8001

# Terminal 3: Frontend
cd Frontend
npm run dev
```

### 4. Create Test Data

```bash
# Option A: Use existing owner portal data
# - Login as owner at http://localhost:5173/auth
# - Create property and courts

# Option B: Get IDs from existing data
cd Backend
python scripts/get_test_ids.py
```

### 5. Test Chatbot

1. Go to: **http://localhost:5173/chatbot-test**
2. Enter User IDs (from step 4)
3. Start chatting!

## Test Messages

```
"Hello"
"Show me available tennis courts"
"I want to book a tennis court"
"What sports do you have?"
```

## Key Points

✅ **owner_profile_id** = Owner Profile ID (NOT user_id)  
✅ **user_id** = Customer's user ID  
✅ Chatbot has its own database (chats, messages)  
✅ Chatbot reads from management database (properties, courts)  
✅ Bookings are created in management database  
✅ Services expect OwnerContext with owner_profile_id

## Architecture

```
Customer (user_id) → Chatbot → Owner Profile (owner_profile_id)
                        ↓
                   Chat Database (async)
                        ↓
                   Management Database (sync)
                        ↓
                   OwnerProfile → Properties → Courts → Bookings
```

## Files Created

- `Frontend/src/pages/customer/ChatbotTest.jsx` - Test UI
- `Frontend/src/pages/customer/chatbotTest.css` - Styles
- `Backend/scripts/get_test_ids.py` - Helper to get IDs
- `Backend/TEST_DATA_SETUP.md` - Data requirements
- `CHATBOT_TESTING_GUIDE.md` - Full testing guide

## Troubleshooting

**Can't connect to chatbot API?**
- Check port 8001 is free
- Verify chatbot API is running
- Check CORS settings

**No properties showing?**
- Verify owner has properties in management DB
- Check owner_profile_id is correct
- Run `get_test_ids.py` to verify data

**LLM errors?**
- Check OPENAI_API_KEY is set
- Verify API key has credits
- Check internet connection

## What's Next?

See `CHATBOT_TESTING_GUIDE.md` for:
- Detailed testing scenarios
- Database verification
- Production deployment
- Feature enhancements

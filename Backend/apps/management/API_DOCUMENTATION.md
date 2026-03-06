# Public API Documentation - Court Search

## Overview
This document describes the public API endpoints for searching and viewing courts in the user portal.

---

## Endpoints

### 1. Search Courts
**Endpoint:** `GET /api/public/courts`

**Description:** Search and filter courts with multiple criteria. Returns courts with property information, media, and base pricing.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| search | string | No | Search in court name, property name, address, or city |
| date | string | No | Date for availability check (YYYY-MM-DD) |
| start_time | string | No | Start time for availability check (HH:MM, requires date) |
| sport_type | string | No | Filter by sport type (futsal, padel, cricket, etc.) |
| min_price | float | No | Minimum price per hour |
| max_price | float | No | Maximum price per hour |
| page | int | No | Page number (default: 1) |
| limit | int | No | Items per page (default: 20, max: 100) |

**Example Requests:**

```bash
# Search by name
GET /api/public/courts?search=Arena

# Search with date and time availability
GET /api/public/courts?date=2024-03-15&start_time=14:00

# Search with multiple filters
GET /api/public/courts?search=Karachi&sport_type=futsal&min_price=1000&max_price=3000

# Search with pagination
GET /api/public/courts?page=2&limit=10
```

**Response Format:**
```json
{
  "success": true,
  "message": "Courts retrieved successfully",
  "data": {
    "items": [
      {
        "id": 1,
        "name": "Court A",
        "sport_type": "Futsal",
        "description": "Premium indoor futsal court",
        "specifications": {
          "is_indoor": true,
          "surface_type": "Turf",
          "dimensions": "40x20"
        },
        "amenities": ["Parking", "Changing Room", "Cafeteria"],
        "base_price": 1500.0,
        "is_indoor": true,
        "surface_type": "Turf",
        "property": {
          "id": 1,
          "name": "Sports Arena",
          "address": "123 Main Street, Karachi",
          "city": "Karachi",
          "state": "Sindh",
          "phone": "+92-300-1234567",
          "email": "info@arena.com",
          "maps_link": "https://maps.google.com/...",
          "amenities": ["Parking", "Security", "WiFi"]
        },
        "media": [
          {
            "id": 1,
            "media_type": "image",
            "url": "https://example.com/court1.jpg",
            "thumbnail_url": "https://example.com/court1_thumb.jpg",
            "caption": "Main court view"
          }
        ],
        "is_available": true
      }
    ],
    "total": 50,
    "page": 1,
    "limit": 20,
    "pages": 3
  }
}
```

**Notes:**
- `is_available` field only appears when both `date` and `start_time` are provided
- Search is case-insensitive and uses partial matching (LIKE)
- Price filter uses the minimum price from all pricing rules for that court

---

### 2. Get Court Details
**Endpoint:** `GET /api/public/courts/{court_id}`

**Description:** Get detailed information about a specific court including property details, pricing rules, and media.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| court_id | int | Yes | Court ID |

**Example Request:**
```bash
GET /api/public/courts/1
```

**Response Format:**
```json
{
  "success": true,
  "message": "Court details retrieved successfully",
  "data": {
    "id": 1,
    "name": "Court A",
    "sport_type": "Futsal",
    "description": "Premium indoor futsal court",
    "specifications": {
      "is_indoor": true,
      "surface_type": "Turf"
    },
    "amenities": ["Parking", "Changing Room"],
    "property": {
      "id": 1,
      "name": "Sports Arena",
      "address": "123 Main Street, Karachi",
      "city": "Karachi",
      "maps_link": "https://maps.google.com/..."
    },
    "pricing_rules": [
      {
        "id": 1,
        "days": [0, 1, 2, 3, 4],
        "start_time": "06:00:00",
        "end_time": "18:00:00",
        "price_per_hour": 1500.0,
        "label": "Weekday Morning"
      }
    ],
    "media": [
      {
        "id": 1,
        "media_type": "image",
        "url": "https://example.com/court1.jpg",
        "thumbnail_url": "https://example.com/court1_thumb.jpg",
        "caption": "Main court view"
      }
    ]
  }
}
```

---

### 3. Get Available Slots
**Endpoint:** `GET /api/public/courts/{court_id}/availability`

**Description:** Get all available time slots for a court on a specific date.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| court_id | int | Yes | Court ID |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| date | string | Yes | Date to check (YYYY-MM-DD) |

**Example Request:**
```bash
GET /api/public/courts/1/availability?date=2024-03-15
```

**Response Format:**
```json
{
  "success": true,
  "message": "Available slots retrieved successfully",
  "data": {
    "date": "2024-03-15",
    "court_id": 1,
    "court_name": "Court A",
    "available_slots": [
      {
        "start_time": "06:00:00",
        "end_time": "07:00:00",
        "price_per_hour": 1500.0,
        "label": "Weekday Morning"
      },
      {
        "start_time": "07:00:00",
        "end_time": "08:00:00",
        "price_per_hour": 1500.0,
        "label": "Weekday Morning"
      }
    ]
  }
}
```

**Notes:**
- Only returns slots that are:
  - Within court's pricing hours
  - Not blocked by owner
  - Not already booked (pending or confirmed)
- Slots are 1-hour intervals

---

## Implementation Details

### Architecture
```
Frontend Request
    ↓
Router (public.py) - Validates parameters
    ↓
Service (public_service.py) - Business logic
    ↓
Repository (court_repo.py) - Database queries
    ↓
Database (PostgreSQL)
```

### Database Queries
The search endpoint performs optimized queries with:
- JOINs with Property, CourtPricing, CourtMedia tables
- Filters applied at database level
- Pagination to handle large datasets
- Eager loading to avoid N+1 queries

### Performance Considerations
- Indexes on: `court.name`, `property.address`, `court.sport_type`
- Distinct queries to avoid duplicates from pricing joins
- Pagination limits maximum results per request
- Eager loading with `joinedload()` for related data

### Future Enhancements
- [ ] Add Redis caching for popular searches
- [ ] Implement full-text search with PostgreSQL
- [ ] Add geolocation-based distance search
- [ ] Add sorting options (price, distance, rating)
- [ ] Add court ratings and reviews

---

## Error Responses

### Court Not Found (404)
```json
{
  "success": false,
  "message": "Court not found",
  "data": null
}
```

### Invalid Parameters (422)
```json
{
  "detail": [
    {
      "loc": ["query", "min_price"],
      "msg": "ensure this value is greater than or equal to 0",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

### Server Error (500)
```json
{
  "success": false,
  "message": "Internal server error",
  "data": null
}
```

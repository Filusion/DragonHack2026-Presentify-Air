# API Reference

Complete API documentation for Presentify-Air Backend.

## Base URL

```
http://localhost:8000
```

---

## Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Description:** Check system health and get connection statistics.

**Request:**
```http
GET /health HTTP/1.1
Host: localhost:8000
```

**Response:** `200 OK`
```json
{
  "status": "ok",
  "vision": true,
  "speech": true,
  "websocket_clients": 3
}
```

**Response Schema:**
- `status` (string): System status ("ok")
- `vision` (boolean): Vision system availability
- `speech` (boolean): Speech system availability  
- `websocket_clients` (integer): Number of active WebSocket connections

---

### 2. Get Session State

**Endpoint:** `GET /session/{session_id}`

**Description:** Retrieve current state for a specific session.

**Path Parameters:**
- `session_id` (string): Session identifier (currently only "default" is supported)

**Request:**
```http
GET /session/default HTTP/1.1
Host: localhost:8000
```

**Response:** `200 OK`
```json
{
  "session_id": "default",
  "active": true,
  "focus_mode": false,
  "last_captured_frame": "iVBORw0KGgoAAAANS...",
  "timeline_size": 147,
  "recent_events": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "type": "command",
      "action": "next_slide",
      "source": "frontend",
      "timestamp": 1713456789.123,
      "payload": {}
    }
  ]
}
```

**Response Schema:**
- `session_id` (string): Session identifier
- `active` (boolean): Whether session is active
- `focus_mode` (boolean): Whether focus mode is enabled
- `last_captured_frame` (string | null): Base64-encoded last camera frame
- `timeline_size` (integer): Total events in timeline
- `recent_events` (array): Last 20 events from timeline

**Error Responses:**

`404 Not Found`
```json
{
  "detail": "session_not_found"
}
```

---

### 3. Send Command

**Endpoint:** `POST /command`

**Description:** Send a generic command to the system.

**Request Body:**
```json
{
  "action": "next_slide",
  "source": "frontend",
  "payload": {
    "custom_field": "custom_value"
  }
}
```

**Request Schema:**
- `action` (string, required): Action to perform
- `source` (string, optional): Event source ("frontend" | "speech" | "vision" | "system"), defaults to "frontend"
- `payload` (object, optional): Additional data, defaults to {}

**Common Actions:**
- `next_slide`: Advance to next slide
- `previous_slide`: Go to previous slide
- `start_presentation`: Start presentation mode
- `end_presentation`: Exit presentation mode
- `save_board`: Save current board frame

**Request:**
```http
POST /command HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "action": "next_slide",
  "source": "frontend"
}
```

**Response:** `200 OK`
```json
{
  "status": "ok",
  "event": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "command",
    "action": "next_slide",
    "source": "frontend",
    "timestamp": 1713456789.123,
    "payload": {}
  },
  "side_effects": {
    "presentation": {
      "status": "queued",
      "action": "next_slide",
      "mapped_key": "right"
    }
  }
}
```

**Error Responses:**

`429 Too Many Requests` (Cooldown violation)
```json
{
  "detail": "next_slide_cooldown_active"
}
```

---

### 4. Start Focus Mode

**Endpoint:** `POST /focus/start`

**Description:** Enable focus mode (typically disables distractions/notifications).

**Request:**
```http
POST /focus/start HTTP/1.1
Host: localhost:8000
```

**Response:** `200 OK`
```json
{
  "status": "ok",
  "event": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "system",
    "action": "focus_start",
    "source": "frontend",
    "timestamp": 1713456789.123,
    "payload": {}
  }
}
```

---

### 5. Stop Focus Mode

**Endpoint:** `POST /focus/stop`

**Description:** Disable focus mode.

**Request:**
```http
POST /focus/stop HTTP/1.1
Host: localhost:8000
```

**Response:** `200 OK`
```json
{
  "status": "ok",
  "event": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "system",
    "action": "focus_stop",
    "source": "frontend",
    "timestamp": 1713456789.123,
    "payload": {}
  }
}
```

---

### 6. Save Board

**Endpoint:** `POST /save-board`

**Description:** Save the current whiteboard/screen capture.

**Prerequisites:** A camera frame must have been captured via `/vision/frame` first.

**Request:**
```http
POST /save-board HTTP/1.1
Host: localhost:8000
```

**Response:** `200 OK`
```json
{
  "status": "ok",
  "event": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "command",
    "action": "save_board",
    "source": "frontend",
    "timestamp": 1713456789.123,
    "payload": {}
  },
  "side_effects": {
    "board_saved": {
      "status": "queued",
      "timestamp": 1713456789.123
    }
  }
}
```

**Error Responses:**

`409 Conflict` (No frame available)
```json
{
  "detail": "no_board_frame_available"
}
```

`429 Too Many Requests` (Cooldown: 2 seconds)
```json
{
  "detail": "save_board_cooldown_active"
}
```

---

### 7. Vision Frame

**Endpoint:** `POST /vision/frame`

**Description:** Submit a camera frame with optional gesture detection and object detection results.

**Request Body:**
```json
{
  "source": "vision",
  "image_b64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
  "gesture": "gesture_next_slide",
  "detected_objects": ["person", "hand", "marker"],
  "payload": {
    "confidence": 0.95,
    "processing_time_ms": 42
  }
}
```

**Request Schema:**
- `source` (string, optional): Event source, defaults to "vision"
- `image_b64` (string | null, optional): Base64-encoded image data
- `gesture` (string | null, optional): Detected gesture name
- `detected_objects` (array, optional): List of detected objects in frame
- `payload` (object, optional): Additional metadata

**Recognized Gestures:**
- `gesture_next_slide`: Triggers next slide action
- `gesture_previous_slide`: Triggers previous slide action
- `gesture_save_board`: Triggers save board action

**Request:**
```http
POST /vision/frame HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "image_b64": "iVBORw0KGgoAAAA...",
  "gesture": "gesture_next_slide",
  "detected_objects": ["person", "hand"]
}
```

**Response:** `200 OK`
```json
{
  "status": "ok",
  "event": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "vision",
    "action": "next_slide",
    "source": "vision",
    "timestamp": 1713456789.123,
    "payload": {
      "detected_objects": ["person", "hand"]
    }
  },
  "side_effects": {
    "presentation": {
      "status": "queued",
      "action": "next_slide",
      "mapped_key": "right"
    }
  }
}
```

**Notes:**
- If `image_b64` is provided, it's stored as `last_captured_frame`
- If no `gesture` is provided, the action defaults to `"frame_received"`
- Detected objects are merged into the event payload

---

### 8. WebSocket Connection

**Endpoint:** `WS /ws`

**Description:** Real-time bidirectional connection for receiving state updates.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  console.log('Connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected');
};
```

**Initial Message (Session Snapshot):**

Immediately after connection, server sends current state:

```json
{
  "type": "session_snapshot",
  "data": {
    "session_id": "default",
    "active": true,
    "focus_mode": false,
    "last_captured_frame": null,
    "timeline_size": 0,
    "recent_events": []
  }
}
```

**Update Messages (Timeline Updates):**

Whenever an event is processed, all connected clients receive:

```json
{
  "type": "timeline_update",
  "data": {
    "event": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "type": "command",
      "action": "next_slide",
      "source": "frontend",
      "timestamp": 1713456789.123,
      "payload": {}
    },
    "session": {
      "session_id": "default",
      "active": true,
      "focus_mode": false,
      "last_captured_frame": null,
      "timeline_size": 1,
      "recent_events": [...]
    },
    "side_effects": {
      "presentation": {
        "status": "queued",
        "action": "next_slide",
        "mapped_key": "right"
      }
    }
  }
}
```

**Message Types:**
- `session_snapshot`: Full session state (sent on connect)
- `timeline_update`: Event processed, state updated

**Important:** 
- WebSocket is primarily **server → client** (one-way broadcast)
- Clients should send commands via HTTP POST endpoints, not through WebSocket
- The WebSocket connection stays alive by the server waiting for messages (which keeps the connection open)

---

## Data Models

### Event

```typescript
{
  id: string;              // UUID v4
  type: "command" | "vision" | "system";
  action: string;          // e.g., "next_slide", "save_board"
  source: "speech" | "vision" | "frontend" | "system";
  timestamp: number;       // Unix timestamp (seconds)
  payload: object;         // Additional data
}
```

### SessionSnapshot

```typescript
{
  session_id: string;
  active: boolean;
  focus_mode: boolean;
  last_captured_frame: string | null;  // Base64 image
  timeline_size: number;
  recent_events: Event[];              // Last 20 events
}
```

---

## Cooldowns

Actions with cooldown periods to prevent accidental rapid-fire:

| Action | Cooldown | HTTP Error Code |
|--------|----------|-----------------|
| `next_slide` | 1.0 second | 429 |
| `previous_slide` | 1.0 second | 429 |
| `save_board` | 2.0 seconds | 429 |

---

## Error Codes

| Code | Description | Example |
|------|-------------|---------|
| 404 | Resource not found | Invalid session_id |
| 409 | Conflict/Precondition failed | No frame available for save_board |
| 429 | Rate limit exceeded | Action triggered within cooldown period |
| 500 | Internal server error | Unexpected server failure |

---

## Rate Limiting

Currently implemented via cooldowns (per-action). No global rate limiting.

**Future Consideration:** Implement per-client rate limiting for abuse prevention.

---

## Examples

### Complete Flow: Gesture Control

```bash
# 1. Connect to WebSocket (in separate terminal)
websocat ws://localhost:8000/ws

# 2. Send camera frame with gesture
curl -X POST http://localhost:8000/vision/frame \
  -H "Content-Type: application/json" \
  -d '{
    "image_b64": "iVBORw0KGgoAAAA...",
    "gesture": "gesture_next_slide",
    "detected_objects": ["person", "hand"]
  }'

# WebSocket receives:
# {
#   "type": "timeline_update",
#   "data": {
#     "event": { "action": "next_slide", ... },
#     "session": { ... },
#     "side_effects": { "presentation": { "mapped_key": "right" } }
#   }
# }

# 3. Wait 1 second (cooldown)

# 4. Send another command
curl -X POST http://localhost:8000/command \
  -H "Content-Type: application/json" \
  -d '{"action": "previous_slide"}'
```

### Save Board Flow

```bash
# 1. Capture a frame first
curl -X POST http://localhost:8000/vision/frame \
  -H "Content-Type: application/json" \
  -d '{
    "image_b64": "base64_whiteboard_image..."
  }'

# 2. Save the board
curl -X POST http://localhost:8000/save-board

# Response:
# {
#   "status": "ok",
#   "side_effects": {
#     "board_saved": {
#       "status": "queued",
#       "timestamp": 1713456789.123
#     }
#   }
# }
```

---

## Testing

### Using cURL

```bash
# Health check
curl http://localhost:8000/health

# Send command
curl -X POST http://localhost:8000/command \
  -H "Content-Type: application/json" \
  -d '{"action": "next_slide"}'

# Get session
curl http://localhost:8000/session/default

# Enable focus mode
curl -X POST http://localhost:8000/focus/start
```

### Using Python

```python
import requests

# Send command
response = requests.post(
    'http://localhost:8000/command',
    json={'action': 'next_slide', 'source': 'frontend'}
)
print(response.json())

# Connect to WebSocket
import asyncio
import websockets

async def listen():
    async with websockets.connect('ws://localhost:8000/ws') as websocket:
        async for message in websocket:
            print(f"Received: {message}")

asyncio.run(listen())
```

### Using JavaScript

```javascript
// Send command
fetch('http://localhost:8000/command', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ action: 'next_slide' })
})
.then(res => res.json())
.then(data => console.log(data));

// WebSocket
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
  console.log('Update:', JSON.parse(event.data));
};
```

---

## Interactive API Docs

FastAPI automatically generates interactive documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

These interfaces allow you to:
- View all endpoints
- See request/response schemas
- Test endpoints directly in the browser
- Download OpenAPI specification

# Architecture & Component Interaction Guide

This document explains how the different components interact and the data flow through the system.

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Inputs                          │
└─────────────────────────────────────────────────────────────────┘
        │                    │                    │
        │ Camera Frames      │ Voice Commands     │ UI Button Clicks
        │ + Gestures         │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Vision     │    │    Speech    │    │   Frontend   │
│   Client     │    │    Client    │    │     UI       │
└──────────────┘    └──────────────┘    └──────────────┘
        │                    │                    │
        │ POST /vision/frame │ POST /command      │ POST /command
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
        ┌────────────────────────────────────────────────┐
        │           FastAPI Application                  │
        │  ┌──────────────────────────────────────────┐  │
        │  │          Route Handlers                  │  │
        │  │  /health  /command  /vision/frame  /ws   │  │
        │  └──────────────────────────────────────────┘  │
        │                     │                          │
        │                     ▼                          │
        │  ┌──────────────────────────────────────────┐  │
        │  │         EventProcessor                   │  │
        │  │  • Normalize events                      │  │
        │  │  • Validate cooldowns                    │  │
        │  │  • Execute side effects                  │  │
        │  │  • Orchestrate components                │  │
        │  └──────────────────────────────────────────┘  │
        │           │              │              │       │
        │           ▼              ▼              ▼       │
        │  ┌─────────────┐ ┌──────────────┐ ┌─────────┐ │
        │  │   Session   │ │ Presentation │ │Connection│ │
        │  │   Manager   │ │  Controller  │ │ Manager │ │
        │  └─────────────┘ └──────────────┘ └─────────┘ │
        │           │              │              │       │
        │           ▼              ▼              ▼       │
        │  ┌─────────────┐ ┌──────────────┐ ┌─────────┐ │
        │  │ SessionState│ │ Key Mappings │ │ WebSocket│ │
        │  │  Timeline   │ │              │ │   Pool   │ │
        │  └─────────────┘ └──────────────┘ └─────────┘ │
        └────────────────────────────────────────────────┘
                                  │
                                  │ WebSocket Broadcast
                                  ▼
        ┌─────────────────────────────────────────────┐
        │           Connected Clients (WS)             │
        │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
        │  │ Client A │  │ Client B │  │ Client C │  │
        │  └──────────┘  └──────────┘  └──────────┘  │
        └─────────────────────────────────────────────┘
```

---

## Component Interaction Patterns

### Pattern 1: Event Processing Pipeline

Every action flows through the same pipeline:

```
Input (HTTP Request)
    ↓
Create Event Object
    ↓
EventProcessor.process()
    ↓
┌─────────────────────────┐
│ 1. Normalize            │ ← Convert gesture names to actions
├─────────────────────────┤
│ 2. Validate             │ ← Check cooldowns
├─────────────────────────┤
│ 3. Execute Side Effects │ ← Toggle focus, queue presentation controls
├─────────────────────────┤
│ 4. Record Event         │ ← Append to timeline
├─────────────────────────┤
│ 5. Broadcast Update     │ ← Notify all WebSocket clients
└─────────────────────────┘
    ↓
Return Response (HTTP)
```

### Pattern 2: State Management

State is centralized and thread-safe:

```
┌──────────────────────┐
│   SessionManager     │
│  (with asyncio.Lock) │
└──────────────────────┘
          │
          │ protects
          ▼
┌──────────────────────┐
│   SessionState       │
│  • session_id        │
│  • active            │
│  • focus_mode        │
│  • last_frame        │
│  • timeline (deque)  │
│  • cooldown_tracker  │
└──────────────────────┘

Multiple concurrent requests
    ↓           ↓           ↓
Request A   Request B   Request C
    ↓           ↓           ↓
    └───────────┼───────────┘
                │
         Lock ensures only
         one modifies state
         at a time
                │
                ▼
        State Updated
```

### Pattern 3: WebSocket Broadcasting

State changes propagate to all clients:

```
Event Processed
    ↓
┌──────────────────────────┐
│ ConnectionManager        │
│ .broadcast(message)      │
└──────────────────────────┘
    ↓
    Iterate over active connections
    ↓           ↓           ↓
Client A    Client B    Client C
    ↓           ↓           ✗ (connection failed)
   Send        Send         │
   ✓           ✓            │
                            ▼
                    Mark as stale,
                    remove from pool
```

---

## Data Flow Examples

### Example 1: Next Slide via Gesture

```
1. Camera System
   └─> Detects swipe right gesture
   └─> POST /vision/frame
       {
         "gesture": "gesture_next_slide",
         "image_b64": "...",
         "detected_objects": ["person", "hand"]
       }

2. FastAPI Route Handler (/vision/frame)
   └─> Store image: SessionManager.set_last_frame()
   └─> Create Event:
       Event(
         type="vision",
         action="gesture_next_slide",  ← Will be normalized
         source="vision",
         payload={"detected_objects": ["person", "hand"]}
       )
   └─> Call EventProcessor.process(event)

3. EventProcessor._normalize_event()
   └─> gesture_map lookup:
       "gesture_next_slide" → "next_slide"
   └─> Return normalized Event with action="next_slide"

4. EventProcessor._validate_event()
   └─> Get last trigger time for "next_slide"
   └─> Check if (current_time - last_trigger) < 1.0 second
   └─> ✓ Valid (or raise HTTP 429)

5. EventProcessor.process() - Execute Side Effects
   └─> Identify action: "next_slide" is a presentation control
   └─> Call PresentationController.send("next_slide")
       Returns: {
         "status": "queued",
         "action": "next_slide",
         "mapped_key": "right"
       }
   └─> Store in side_effects dict

6. EventProcessor.process() - Record Event
   └─> SessionManager.append_event(normalized_event)
       ├─> Append to timeline (deque)
       └─> Update last_trigger_by_action["next_slide"] = timestamp

7. EventProcessor.process() - Broadcast
   └─> ConnectionManager.broadcast({
         "type": "timeline_update",
         "data": {
           "event": {...},
           "session": SessionState.snapshot(),
           "side_effects": {"presentation": {...}}
         }
       })
   └─> All WebSocket clients receive update

8. Return HTTP Response
   └─> {
         "status": "ok",
         "event": {...},
         "side_effects": {"presentation": {...}}
       }

9. External Worker (Not Shown in Code)
   └─> Listens for "queued" presentation controls
   └─> Simulates "right arrow" key press
   └─> PowerPoint/Slides advances to next slide
```

### Example 2: Save Board Operation

```
1. Background: Frame Already Captured
   └─> Earlier POST /vision/frame stored image in:
       SessionState.last_captured_frame = "base64_image..."

2. User Triggers Save
   └─> POST /save-board
   └─> Creates Event(type="command", action="save_board")

3. EventProcessor.process()
   └─> Validation:
       ├─> Check cooldown (2.0 seconds for save_board)
       └─> Check SessionState.last_captured_frame is not None
           (raises HTTP 409 if None)

4. Execute Side Effects
   └─> side_effects["board_saved"] = {
         "status": "queued",
         "timestamp": 1713456789.123
       }

5. Record & Broadcast
   └─> Event appended to timeline
   └─> All clients receive timeline_update

6. External Worker (Hypothetical)
   └─> Detects "board_saved" in side_effects
   └─> Retrieves SessionState.last_captured_frame
   └─> Decodes base64 → image bytes
   └─> Saves to disk: board_2024_04_18_14_32_15.png
   └─> (Optional) Uploads to cloud storage
```

### Example 3: Focus Mode Toggle

```
1. User Clicks "Focus" Button
   └─> POST /focus/start

2. Route Handler
   └─> Creates Event(type="system", action="focus_start")

3. EventProcessor.process()
   └─> Identifies action="focus_start"
   └─> Calls SessionManager.set_focus_mode(True)
       ├─> Acquires lock
       ├─> Sets SessionState.focus_mode = True
       └─> Releases lock

4. Broadcast Update
   └─> WebSocket clients receive:
       {
         "type": "timeline_update",
         "data": {
           "session": {"focus_mode": true, ...},
           ...
         }
       }

5. Frontend Receives Update
   └─> Checks data.session.focus_mode === true
   └─> Updates UI:
       ├─> Hides notifications
       ├─> Dims background
       └─> Shows "Focus Mode Active" indicator
```

---

## Concurrency Handling

### SessionManager Lock

```python
# Multiple requests arrive simultaneously
Request A: POST /command {"action": "next_slide"}
Request B: POST /command {"action": "previous_slide"}
Request C: POST /vision/frame {"gesture": "gesture_save_board"}

# All try to modify SessionState

async with self._lock:  # Request A acquires lock first
    self._session.timeline.append(event_A)
    self._session.last_trigger_by_action["next_slide"] = time_A
    # Lock released

async with self._lock:  # Request B acquires lock second
    self._session.timeline.append(event_B)
    self._session.last_trigger_by_action["previous_slide"] = time_B
    # Lock released

async with self._lock:  # Request C acquires lock third
    self._session.timeline.append(event_C)
    self._session.last_trigger_by_action["save_board"] = time_C
    # Lock released

# All events safely recorded in order
```

### WebSocket Connection Pool

```python
# ConnectionManager maintains set of active connections
active_connections = {ws1, ws2, ws3, ws4, ws5}

# During broadcast, if ws3 fails:
async def broadcast(message):
    stale = []
    for ws in active_connections:
        try:
            await ws.send_json(message)
        except RuntimeError:
            stale.append(ws)  # ws3 added to stale
    
    for ws in stale:
        active_connections.discard(ws)  # ws3 removed

# Pool automatically cleaned: {ws1, ws2, ws4, ws5}
```

---

## Cooldown Mechanism

### How Cooldowns Prevent Double-Triggers

```
Timeline:
0.0s  │ User makes "next" gesture
      │ ↓
      │ SessionState.last_trigger_by_action["next_slide"] = 0.0
      │ Event processed ✓
      │
0.5s  │ User accidentally makes "next" gesture again
      │ ↓
      │ Check: (0.5 - 0.0) < 1.0?  → YES
      │ Reject with HTTP 429 ✗
      │
1.2s  │ User makes "next" gesture deliberately
      │ ↓
      │ Check: (1.2 - 0.0) < 1.0?  → NO
      │ SessionState.last_trigger_by_action["next_slide"] = 1.2
      │ Event processed ✓
```

### Cooldown Configuration

```python
# In EventProcessor.__init__()
self.cooldowns = {
    "next_slide": 1.0,        # Wait 1 second between next slides
    "previous_slide": 1.0,    # Wait 1 second between previous slides
    "save_board": 2.0,        # Wait 2 seconds between saves
}

# Actions NOT in this dict have no cooldown (process immediately)
```

---

## WebSocket Message Flow

### Connection Lifecycle

```
Client                           Server
  │                                │
  │───────── WS Connect ──────────▶│
  │                                │ ConnectionManager.connect()
  │                                │ active_connections.add(ws)
  │                                │
  │◀─── session_snapshot ──────────│ Immediate state sync
  │                                │
  │                                │
  │                (Events happen) │
  │                                │
  │◀─── timeline_update ───────────│ Broadcast #1
  │                                │
  │◀─── timeline_update ───────────│ Broadcast #2
  │                                │
  │                                │
  │──────── (keep-alive) ─────────▶│ websocket.receive_text()
  │                                │ (infinite loop keeps connection open)
  │                                │
  │─────── Disconnect ─────────────│
  │                                │ WebSocketDisconnect exception
  │                                │ ConnectionManager.disconnect()
  │                                │ active_connections.discard(ws)
```

### Message Types

#### session_snapshot (sent on connect)
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

#### timeline_update (sent on every event)
```json
{
  "type": "timeline_update",
  "data": {
    "event": {
      "id": "...",
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

---

## Extension Points

### Adding New Actions

1. **Add to gesture map** (if gesture-triggered):
```python
# In EventProcessor._normalize_event()
gesture_map = {
    "gesture_pause_presentation": "pause_presentation",  # NEW
}
```

2. **Add cooldown** (if needed):
```python
# In EventProcessor.__init__()
self.cooldowns = {
    "pause_presentation": 0.5,  # NEW
}
```

3. **Add key mapping** (if presentation control):
```python
# In PresentationController.send()
key_map = {
    "pause_presentation": "b",  # NEW: "b" key pauses in PowerPoint
}
```

4. **Add side effect logic** (if special behavior):
```python
# In EventProcessor.process()
if normalized_event.action == "pause_presentation":
    side_effects["presentation"] = await self.presentation_controller.send(
        normalized_event.action
    )
```

### Adding New Event Sources

```python
# 1. Add to EventSource type
EventSource = Literal["speech", "vision", "frontend", "system", "mobile_app"]  # NEW

# 2. Create new endpoint
@app.post("/mobile/command")
async def mobile_command(request: CommandRequest) -> dict[str, Any]:
    event = Event(
        type="command",
        action=request.action,
        source="mobile_app",  # NEW source
        payload=request.payload
    )
    result = await event_processor.process(event)
    return {"status": "ok", "event": result["event"].model_dump()}
```

---

## Performance Considerations

### Memory Usage

```
SessionState.timeline = deque(maxlen=500)
├─> Each Event ≈ 200 bytes (with small payload)
└─> Max memory: 500 × 200 = 100 KB (negligible)

SessionState.last_captured_frame (base64 image)
├─> 1920×1080 JPEG ≈ 200 KB raw
├─> Base64 encoding ≈ 270 KB
└─> Memory: ~270 KB per stored frame (acceptable)
```

### Scalability Bottlenecks

1. **Single Session Model**
   - Current: One global session (not multi-tenant)
   - Limit: ~100 concurrent users before performance degrades
   - Solution: Implement session pooling with session_id routing

2. **In-Memory Timeline**
   - Current: All events stored in RAM
   - Limit: Timeline growth bounded by maxlen=500
   - Solution: Persist to database for long-term storage

3. **WebSocket Broadcasting**
   - Current: O(n) broadcast to all clients
   - Limit: ~1000 concurrent WebSocket connections
   - Solution: Use Redis pub/sub for horizontal scaling

---

## Security Considerations

### Current State (MVP)

- ❌ No authentication
- ❌ No authorization
- ❌ No input sanitization
- ❌ No rate limiting (except cooldowns)
- ❌ No CORS configuration
- ✓ Type validation (Pydantic models)

### Production Recommendations

1. **Add Authentication**
```python
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.post("/command")
async def command(
    request: CommandRequest,
    token: str = Depends(security)
) -> dict[str, Any]:
    # Verify token
    pass
```

2. **Add Rate Limiting**
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/command")
@limiter.limit("10/minute")
async def command(...):
    pass
```

3. **Sanitize Base64 Images**
```python
import base64

def validate_image(b64: str) -> bool:
    try:
        data = base64.b64decode(b64)
        # Verify it's a valid image format
        return True
    except:
        return False
```

---

## Deployment Architecture

### Development
```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```
┌─────────────────┐
│  Nginx/Caddy    │  ← Reverse proxy, SSL termination
│  (Port 80/443)  │
└────────┬────────┘
         │
    ┌────┴────┐
    │  Load   │
    │ Balancer│
    └────┬────┘
         │
    ┌────┴──────────────┐
    │                   │
┌───▼────┐         ┌────▼───┐
│ Uvicorn│         │Uvicorn │  ← Multiple workers
│ Worker │         │ Worker │
│  :8001 │         │  :8002 │
└────────┘         └────────┘
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Troubleshooting

### Common Issues

**Issue:** WebSocket clients not receiving updates
```
Solution: Check ConnectionManager.active_connections
- Verify client connected successfully
- Check for network disconnections
- Look for RuntimeError during broadcast
```

**Issue:** HTTP 429 errors (cooldown active)
```
Solution: Adjust cooldown periods or clear state
- Reduce cooldown in EventProcessor.__init__()
- Restart server to reset last_trigger_by_action
- Implement cooldown bypass for testing
```

**Issue:** "no_board_frame_available" error
```
Solution: Ensure frame captured before save
- POST /vision/frame with image_b64 BEFORE /save-board
- Check SessionState.last_captured_frame is not None
```

---

This architecture enables a flexible, event-driven presentation control system that can scale to support multiple input modalities while maintaining a clean separation of concerns.

# Presentify-Air Backend

A gesture-controlled presentation system backend built with FastAPI that enables hands-free presentation control through computer vision, voice commands, and traditional UI inputs.

## 🎯 What Does This Do?

Presentify-Air allows you to control presentations (PowerPoint, Google Slides, etc.) using:
- **Hand gestures** detected by your camera
- **Voice commands** 
- **Traditional UI buttons** as fallback

All connected clients receive real-time updates via WebSocket, making it perfect for collaborative or remote presentation scenarios.

---

## 🏗️ Architecture Overview

```
┌─────────────┐
│   Camera    │──┐
└─────────────┘  │
                 │
┌─────────────┐  │    ┌──────────────────┐
│  Frontend   │──┼───▶│  FastAPI Server  │
└─────────────┘  │    └──────────────────┘
                 │            │
┌─────────────┐  │            │
│    Voice    │──┘            ▼
└─────────────┘        ┌─────────────┐
                       │  WebSocket  │
                       │  Broadcast  │
                       └─────────────┘
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
               Client A   Client B   Client C
```

### Event-Driven Design

The system uses **event sourcing** - every action (gesture, command, state change) becomes an immutable event stored in a timeline. This provides:
- Complete audit trail
- Easy debugging (replay events)
- Real-time state synchronization across clients

---

## 📦 Core Components

### 1. **Event System**

All actions flow through a unified event model:

```python
class Event:
    id: str              # Unique identifier (UUID)
    type: EventType      # "command" | "vision" | "system"
    action: str          # What to do (e.g., "next_slide")
    source: EventSource  # Where it came from ("speech" | "vision" | "frontend")
    timestamp: float     # When it occurred
    payload: dict        # Additional data
```

**Event Types:**
- `command`: User-initiated actions (next slide, save board)
- `vision`: Computer vision detections (gestures, objects)
- `system`: Internal state changes (focus mode toggle)

**Event Sources:**
- `speech`: Voice commands
- `vision`: Camera/gesture detection
- `frontend`: UI button clicks
- `system`: Automated triggers

### 2. **SessionState**

The single source of truth for application state:

```python
@dataclass
class SessionState:
    session_id: str                              # Session identifier
    active: bool                                 # Is session active?
    focus_mode: bool                             # Focus mode enabled?
    last_captured_frame: str | None              # Latest camera frame (base64)
    timeline: deque[Event]                       # Last 500 events
    last_trigger_by_action: dict[str, float]     # Cooldown tracking
```

**Key Features:**
- **Timeline**: Circular buffer storing last 500 events (event history)
- **Cooldown Tracking**: Prevents accidental rapid-fire actions
- **Focus Mode**: Can disable distractions/notifications
- **Frame Storage**: Keeps latest camera frame for board saving

### 3. **SessionManager**

Thread-safe wrapper around `SessionState` using `asyncio.Lock`:

**Why the lock?** Multiple concurrent requests could try to modify state simultaneously. The lock ensures race-condition-free updates.

**Methods:**
- `get_session()`: Returns current session state
- `append_event()`: Adds event to timeline and updates cooldown tracker
- `set_focus_mode()`: Toggles focus mode
- `set_last_frame()`: Updates stored camera frame
- `last_triggered_at()`: Gets timestamp of last action (for cooldown checks)

### 4. **ConnectionManager**

Manages WebSocket connections for real-time client updates:

**Methods:**
- `connect()`: Accepts new WebSocket connection
- `disconnect()`: Removes connection from active pool
- `broadcast()`: Sends message to all connected clients

**Smart Cleanup:** Automatically detects and removes stale connections (clients that disconnected without proper cleanup).

### 5. **PresentationController**

Maps high-level actions to keyboard shortcuts:

```python
Action Mapping:
├─ next_slide        → Right Arrow
├─ previous_slide    → Left Arrow
├─ start_presentation→ F5
└─ end_presentation  → Esc
```

**Note:** This component returns metadata only. Actual key presses happen in a separate worker process or frontend component.

### 6. **EventProcessor** (The Brain 🧠)

Orchestrates the entire event lifecycle:

1. **Normalize** - Converts gesture names to canonical actions
2. **Validate** - Enforces cooldown periods
3. **Execute** - Performs side effects
4. **Record** - Appends to timeline
5. **Broadcast** - Notifies all clients

**Gesture Normalization:**
```python
gesture_next_slide     → next_slide
gesture_previous_slide → previous_slide
gesture_save_board     → save_board
```

This decouples input modality from action semantics (swipe, voice, or button all become "next_slide").

**Cooldown Enforcement:**
```python
Cooldowns:
├─ next_slide     : 1.0 second
├─ previous_slide : 1.0 second
└─ save_board     : 2.0 seconds
```

Prevents accidental double-triggers (e.g., gesture detected twice).

---

## 🔌 API Endpoints

### Health Check
```http
GET /health
```
Returns system status and number of connected WebSocket clients.

**Response:**
```json
{
  "status": "ok",
  "vision": true,
  "speech": true,
  "websocket_clients": 3
}
```

### Get Session State
```http
GET /session/{session_id}
```
Returns current session state including recent events.

**Response:**
```json
{
  "session_id": "default",
  "active": true,
  "focus_mode": false,
  "last_captured_frame": "base64...",
  "timeline_size": 147,
  "recent_events": [...]
}
```

### Send Command
```http
POST /command
Content-Type: application/json

{
  "action": "next_slide",
  "source": "frontend",
  "payload": {}
}
```

Generic endpoint for any command.

**Response:**
```json
{
  "status": "ok",
  "event": {...},
  "side_effects": {
    "presentation": {
      "status": "queued",
      "action": "next_slide",
      "mapped_key": "right"
    }
  }
}
```

### Focus Mode Control
```http
POST /focus/start   # Enable focus mode
POST /focus/stop    # Disable focus mode
```

### Save Board
```http
POST /save-board
```

Saves the current whiteboard/screen capture (requires a frame to be captured first).

**Error Response (409):**
```json
{
  "detail": "no_board_frame_available"
}
```

### Vision Frame
```http
POST /vision/frame
Content-Type: application/json

{
  "image_b64": "base64_encoded_image...",
  "gesture": "gesture_next_slide",
  "detected_objects": ["person", "hand", "marker"],
  "payload": {}
}
```

Receives camera frames and detected gestures from computer vision system.

### WebSocket Connection
```
WS /ws
```

Real-time event stream for state synchronization.

**Connection Flow:**
1. Client connects
2. Server sends initial state snapshot
3. Server broadcasts all subsequent state changes
4. Client receives updates in real-time

**Message Format:**
```json
{
  "type": "timeline_update",
  "data": {
    "event": {...},
    "session": {...},
    "side_effects": {...}
  }
}
```

**Important:** WebSocket is **one-way** (server → client). Clients send commands via HTTP POST, not through WebSocket.

---

## 🔄 Event Flow Examples

### Example 1: Next Slide via Gesture

```
1. Camera detects swipe right gesture
   └─> POST /vision/frame
       {
         "gesture": "gesture_next_slide",
         "image_b64": "..."
       }

2. EventProcessor normalizes gesture
   gesture_next_slide → next_slide

3. Validates cooldown (must be >1s since last next_slide)
   ✓ Valid

4. Executes side effects
   └─> PresentationController.send("next_slide")
       Returns: { "mapped_key": "right" }

5. Appends event to timeline

6. Broadcasts to all WebSocket clients
   └─> { "type": "timeline_update", "data": {...} }
```

### Example 2: Cooldown Violation

```
1. User presses "next" button
   └─> POST /command { "action": "next_slide" }
   ✓ Success

2. User accidentally presses "next" again 0.5s later
   └─> POST /command { "action": "next_slide" }
   ✗ Rejected with HTTP 429
   { "detail": "next_slide_cooldown_active" }
```

### Example 3: Save Board

```
1. Camera captures whiteboard frame
   └─> POST /vision/frame { "image_b64": "..." }
   Stored in session.last_captured_frame

2. User makes "save" gesture
   └─> POST /vision/frame { "gesture": "gesture_save_board" }

3. EventProcessor validates frame exists
   ✓ session.last_captured_frame is not None

4. Queues save operation
   side_effects: { "board_saved": { "status": "queued" } }

5. External worker processes the saved frame
   (implementation not shown in this code)
```

---

## 🛡️ Error Handling

### HTTP 404 - Not Found
```json
{ "detail": "session_not_found" }
```
Requested session ID doesn't exist.

### HTTP 409 - Conflict
```json
{ "detail": "no_board_frame_available" }
```
Tried to save board without capturing a frame first.

### HTTP 429 - Too Many Requests
```json
{ "detail": "next_slide_cooldown_active" }
```
Action triggered too quickly (within cooldown period).

---

## 🚀 Getting Started

### Installation

```bash
pip install fastapi pydantic uvicorn --break-system-packages
```

### Running the Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

FastAPI automatically generates interactive documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 🧪 Testing

### Test Health Endpoint
```bash
curl http://localhost:8000/health
```

### Test Command
```bash
curl -X POST http://localhost:8000/command \
  -H "Content-Type: application/json" \
  -d '{"action": "next_slide", "source": "frontend"}'
```

### Test WebSocket (using `websocat`)
```bash
websocat ws://localhost:8000/ws
```

---

## 🔧 Configuration

### Cooldown Periods

Modify in `EventProcessor.__init__()`:

```python
self.cooldowns = {
    "next_slide": 1.0,      # seconds
    "previous_slide": 1.0,
    "save_board": 2.0,
}
```

### Timeline Size

Modify in `SessionState`:

```python
timeline: deque[Event] = field(default_factory=lambda: deque(maxlen=500))
```

Default: 500 events. Increase for longer history, decrease to save memory.

---

## 🏛️ Design Patterns

1. **Event Sourcing** - All state changes are events in a timeline
2. **CQRS-lite** - Commands via POST, queries via WebSocket broadcasts
3. **Singleton** - Single global session (not multi-tenant)
4. **Observer** - WebSocket clients observe state changes
5. **Strategy** - Different event types trigger different side effects

---

## 🔮 Future Enhancements

- Multi-session support (multiple concurrent presentations)
- Persistent event storage (database integration)
- Authentication/authorization
- Rate limiting per client
- Custom gesture training
- Recording/replay functionality
- Integration with specific presentation software APIs

---

## 📝 Common Questions

### Q: Why use WebSocket if clients don't send messages?
**A:** WebSocket provides low-latency, bidirectional channel. Even though clients currently only receive, the connection stays open for instant updates without polling.

### Q: What happens to "queued" actions?
**A:** The current code only marks actions as "queued". An external worker (not shown) likely consumes these events and performs actual keyboard simulation.

### Q: Can multiple users control the same presentation?
**A:** Yes! All commands are processed through the same session, and all connected clients see updates. However, there's no conflict resolution if multiple users send commands simultaneously.

### Q: How does gesture detection work?
**A:** This backend receives already-detected gestures. The computer vision system (separate component) processes camera frames and sends results to `/vision/frame`.

### Q: Why store frames as base64?
**A:** Base64 encoding allows binary image data to be transmitted as JSON-safe text. For production, consider binary protocols (MessagePack, Protobuf) for better efficiency.

---

## 📄 License

[Your License Here]

## 👥 Contributors

[Your Team Here]

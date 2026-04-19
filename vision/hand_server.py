"""
hand_server.py — FastAPI WebSocket server that broadcasts hand tracking data
AND gesture events (slide changes, whiteboard open/close) to all clients.

Message types sent to clients:
  1. hand_state  — continuous, ~60fps:
     { type: "hand_state", writing, x, y, gesture, hand_visible }

  2. gesture_event — fired once on discrete gestures:
     { type: "gesture_event", gesture: "NEXT_SLIDE"|"PREV_SLIDE"|
                                        "OPEN_WHITEBOARD"|"CLOSE_WHITEBOARD" }

--- BUG FIX (gesture flooding) ---
Previously DISCRETE_GESTURES were enqueued on *every frame* the gesture was
held, flooding the frontend with hundreds of NEXT_SLIDE / OPEN_WHITEBOARD
events per second.  Each event caused a React state update, producing visible
flickering and rapid unintended slide advances.

Fix: a per-gesture cooldown dict (_last_gesture_sent) prevents the same
gesture being fired more than once per GESTURE_COOLDOWN seconds.

--- BUG FIX (silent broadcaster death) ---
event_broadcaster() ran without error handling — a single exception would
silently kill the task and stop all gesture events for the session without
any log output.  The task now catches and logs exceptions and continues.
"""

import asyncio
import json
import threading
import time
import uvicorn
import numpy as np

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from hand_tracker import HandTracker
from gestures import (
    GestureRecognizer,
    GESTURE_WRITING,
    GESTURE_NEXT_SLIDE,
    GESTURE_PREV_SLIDE,
    GESTURE_OPEN_WHITEBOARD,
    GESTURE_CLOSE_WHITEBOARD,
)

HOST          = "0.0.0.0"
PORT          = 8000
TARGET_FPS    = 60
FRAME_BUDGET  = 1.0 / TARGET_FPS

KALMAN_PROCESS_NOISE     = 0.06
KALMAN_MEASUREMENT_NOISE = 0.0008

# How long (seconds) before the same discrete gesture can fire again.
# This prevents a held gesture (e.g. Victory sign held for 2 s) from
# sending dozens of OPEN_WHITEBOARD events to the frontend.
GESTURE_COOLDOWN = 1.0

# ─── Shared state ────────────────────────────────────────────
_hand_state: dict = {
    "writing": False, "x": 0.5, "y": 0.5,
    "gesture": None,  "hand_visible": False,
}
_state_lock        = threading.Lock()
_event_queue       = asyncio.Queue()   # discrete gesture events → frontend
_last_gesture_sent: dict = {}          # gesture → timestamp of last send


def update_state(writing, x, y, gesture, visible):
    with _state_lock:
        _hand_state.update({
            "writing": writing, "x": round(float(x), 4),
            "y": round(float(y), 4), "gesture": gesture,
            "hand_visible": visible,
        })

def get_state():
    with _state_lock:
        return dict(_hand_state)


# ─── Kalman filter ───────────────────────────────────────────
class Kalman2D:
    def __init__(self, q=0.003, r=0.02):
        self.q = q; self.r = r; self.initialized = False
        self.x = np.zeros((4,1)); self.P = np.eye(4)
        self.H = np.array([[1,0,0,0],[0,1,0,0]], dtype=float)
        self.R = np.eye(2) * r; self.I = np.eye(4)

    def reset(self):
        self.initialized = False
        self.x = np.zeros((4,1)); self.P = np.eye(4)

    def step(self, mx, my, dt):
        if not self.initialized:
            self.x = np.array([[mx],[my],[0.],[0.]])
            self.P = np.eye(4); self.initialized = True
            return mx, my
        F = np.array([[1,0,dt,0],[0,1,0,dt],[0,0,1,0],[0,0,0,1]], dtype=float)
        q = self.q; dt2=dt*dt; dt3=dt2*dt; dt4=dt2*dt2
        Q = q*np.array([[dt4/4,0,dt3/2,0],[0,dt4/4,0,dt3/2],
                         [dt3/2,0,dt2,0],[0,dt3/2,0,dt2]])
        self.x = F@self.x; self.P = F@self.P@F.T + Q
        z = np.array([[mx],[my]])
        y = z - self.H@self.x; S = self.H@self.P@self.H.T + self.R
        K = self.P@self.H.T@np.linalg.inv(S)
        self.x += K@y; self.P = (self.I - K@self.H)@self.P
        return float(np.clip(self.x[0,0], 0, 1)), float(np.clip(self.x[1,0], 0, 1))


# ─── Tracking thread ─────────────────────────────────────────
DISCRETE_GESTURES = {GESTURE_NEXT_SLIDE, GESTURE_PREV_SLIDE,
                     GESTURE_OPEN_WHITEBOARD, GESTURE_CLOSE_WHITEBOARD}

def tracking_loop(loop):
    print("[tracker] Starting...")
    tracker    = HandTracker(max_hands=1, detection_confidence=0.5, tracking_confidence=0.4)
    recognizer = GestureRecognizer(
        swipe_threshold=0.18, swipe_window=0.60, swipe_cooldown=1.00,
        wb_hold_frames=5,     write_hold_frames=3,
    )
    kf        = Kalman2D(q=KALMAN_PROCESS_NOISE, r=KALMAN_MEASUREMENT_NOISE)
    print("[tracker] Ready.")
    last_time = time.time()

    try:
        while True:
            t0 = time.time()
            dt = max(1e-3, t0 - last_time); last_time = t0

            frame = tracker.get_frame()
            hands = tracker.get_hands(frame)

            if hands:
                gesture = recognizer.update(hands, frame.shape)
                writing = (gesture == GESTURE_WRITING)
                hand    = hands[0]
                ix = max(0., min(1., float(hand.landmarks[8].x)))
                iy = max(0., min(1., float(hand.landmarks[8].y)))
                sx, sy = kf.step(ix, iy, dt)
                update_state(writing, sx, sy, gesture, True)

                # Queue discrete gesture events — but only once per cooldown window.
                # Without this, a held gesture fires ~60 events/s to the frontend,
                # causing rapid unintended slide advances / whiteboard toggles.
                if gesture in DISCRETE_GESTURES:
                    now        = time.time()
                    last_sent  = _last_gesture_sent.get(gesture, 0)
                    if now - last_sent >= GESTURE_COOLDOWN:
                        _last_gesture_sent[gesture] = now
                        asyncio.run_coroutine_threadsafe(
                            _event_queue.put({"type": "gesture_event", "gesture": gesture}),
                            loop
                        )
            else:
                last = get_state(); kf.reset()
                update_state(False, last["x"], last["y"], None, False)
                # Clear cooldown for all gestures when hand is lost so the next
                # intentional gesture fires immediately once the hand returns.
                _last_gesture_sent.clear()

            elapsed = time.time() - t0
            if FRAME_BUDGET - elapsed > 0:
                time.sleep(FRAME_BUDGET - elapsed)
    finally:
        tracker.release()
        print("[tracker] Stopped.")


# ─── FastAPI ──────────────────────────────────────────────────
app = FastAPI(title="Hand Tracking Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

class ConnectionManager:
    def __init__(self):
        self._conns: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws):
        await ws.accept()
        async with self._lock: self._conns.append(ws)
        print(f"[ws] +1 client ({len(self._conns)} total)")

    async def disconnect(self, ws):
        async with self._lock:
            self._conns = [c for c in self._conns if c is not ws]
        print(f"[ws] -1 client ({len(self._conns)} total)")

    async def broadcast(self, data):
        msg  = json.dumps(data)
        dead = []
        async with self._lock: conns = list(self._conns)
        for ws in conns:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)

manager = ConnectionManager()


@app.on_event("startup")
async def startup():
    loop = asyncio.get_event_loop()
    t = threading.Thread(target=tracking_loop, args=(loop,), daemon=True)
    t.start()
    asyncio.create_task(event_broadcaster())


async def event_broadcaster():
    """
    Drain the gesture event queue and broadcast to all clients.

    BUG FIX: previously an unhandled exception here would silently kill
    the task — all subsequent discrete gesture events would be lost for
    the remainder of the session with no log output.

    Now every iteration is wrapped in try/except so a single bad message
    never terminates the broadcaster.
    """
    while True:
        try:
            event = await _event_queue.get()
            await manager.broadcast(event)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            print(f"[broadcaster] error (continuing): {exc}")
            await asyncio.sleep(0.05)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            state = get_state()
            await ws.send_text(json.dumps({"type": "hand_state", **state}))
            await asyncio.sleep(FRAME_BUDGET)
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        await manager.disconnect(ws)


@app.get("/state")
async def hand_state():
    return get_state()


@app.get("/", response_class=HTMLResponse)
async def test_canvas():
    return open(__file__.replace("hand_server.py", "hand_canvas_test.html"),
                encoding="utf-8").read() if False else """
<!DOCTYPE html><html><head><title>Hand Tracker</title>
<style>*{margin:0;padding:0;box-sizing:border-box}
body{background:#111;display:flex;flex-direction:column;align-items:center;
  justify-content:center;height:100vh;font-family:monospace;color:#eee;gap:12px}
canvas{border:2px solid #444;border-radius:8px}
#g{font-size:22px;font-weight:bold;color:#4f4;min-height:30px}
button{background:#333;color:#eee;border:1px solid #555;padding:6px 14px;
  border-radius:4px;cursor:pointer}</style></head>
<body><div id="g">—</div>
<canvas id="c" width="960" height="540"></canvas>
<div><button onclick="dCtx.clearRect(0,0,960,540)">Clear</button>
<button onclick="mirror=!mirror">Mirror</button></div>
<div id="s">Connecting...</div>
<script>
const c=document.getElementById('c'),ctx=c.getContext('2d');
const d=document.createElement('canvas');d.width=960;d.height=540;
const dCtx=d.getContext('2d');
let mirror=true,writing=false,vis=false,cx=480,cy=270,px=null,py=null,pw=false;
function render(){ctx.clearRect(0,0,960,540);ctx.drawImage(d,0,0);
if(vis){ctx.beginPath();ctx.arc(cx,cy,18,0,Math.PI*2);
ctx.fillStyle=writing?'rgba(0,255,180,0.55)':'rgba(255,255,255,0.35)';ctx.fill();
ctx.strokeStyle=writing?'#0fc':'rgba(255,255,255,0.6)';ctx.lineWidth=2;ctx.stroke();}
requestAnimationFrame(render);}requestAnimationFrame(render);
function conn(){const ws=new WebSocket('ws://localhost:8000/ws');
ws.onopen=()=>{document.getElementById('s').textContent='● Connected';
document.getElementById('s').style.color='#4f4';};
ws.onmessage=e=>{const data=JSON.parse(e.data);
if(data.type==='gesture_event'){document.getElementById('g').textContent='⚡ '+data.gesture;return;}
writing=data.writing;vis=data.hand_visible;
document.getElementById('g').textContent=data.gesture||(vis?'—':'No hand');
if(!vis){px=null;py=null;pw=false;return;}
const rx=mirror?(1-data.x)*960:data.x*960,ry=data.y*540;
cx=rx;cy=ry;
if(writing){if(pw&&px!==null){dCtx.beginPath();dCtx.moveTo(px,py);dCtx.lineTo(rx,ry);
dCtx.strokeStyle='#0fc';dCtx.lineWidth=8;dCtx.lineCap='round';dCtx.stroke();}
px=rx;py=ry;pw=true;}else{px=null;py=null;pw=false;}};
ws.onclose=()=>{document.getElementById('s').textContent='○ Disconnected';
document.getElementById('s').style.color='#f44';setTimeout(conn,2000);};
ws.onerror=()=>ws.close();}conn();
</script></body></html>"""


if __name__ == "__main__":
    print(f"\n=== Hand Tracking Server ===")
    print(f"  Test canvas: http://localhost:{PORT}")
    print(f"  WebSocket:   ws://localhost:{PORT}/ws\n")
    uvicorn.run(app, host=HOST, port=PORT)

/**
 * HandCanvas.jsx
 *
 * Drop-in React component that connects to the hand tracking WebSocket
 * and renders a drawing canvas with a live cursor.
 *
 * USAGE:
 *   import HandCanvas from './HandCanvas';
 *   <HandCanvas wsUrl="ws://localhost:8000/ws" width={960} height={540} />
 *
 * PROPS:
 *   wsUrl    — WebSocket URL of hand_server.py  (default: ws://localhost:8000/ws)
 *   width    — canvas width in px               (default: 960)
 *   height   — canvas height in px              (default: 540)
 *   mirror   — mirror X axis                    (default: true)
 *   onGesture— callback(gestureName) for parent (optional)
 */

import { useEffect, useRef, useState, useCallback } from "react";

// ── Drawing config ────────────────────────────────────────────
const CURSOR_RADIUS  = 18;                      // cursor circle radius (px)
const DRAW_WIDTH     = 8;                       // stroke width when drawing
const DRAW_COLOR     = "#00ffcc";               // drawing stroke color
const CURSOR_IDLE    = "rgba(255,255,255,0.30)";// cursor when not writing
const CURSOR_WRITING = "rgba(0,255,180,0.55)";  // cursor when writing
const SMOOTH_FRAMES  = 4;  // ← TUNE: raise = smoother but slightly laggier cursor

export default function HandCanvas({
  wsUrl    = "ws://localhost:8000/ws",
  width    = 960,
  height   = 540,
  mirror   = true,
  onGesture,
}) {
  // Two canvas refs:
  //   drawRef  — persistent drawing layer (never cleared by animation)
  //   dispRef  — display layer (cleared and recomposed every frame)
  const drawRef  = useRef(null);   // offscreen persistent strokes
  const dispRef  = useRef(null);   // visible canvas shown to user

  // Hand state from WebSocket
  const handRef = useRef({
    writing:    false,
    x:          0.5,
    y:          0.5,
    visible:    false,
    gesture:    null,
  });

  // Drawing state
  const drawState = useRef({
    prevX:      null,
    prevY:      null,
    wasWriting: false,
    history:    [],   // smoothing position history
  });

  const [connected, setConnected] = useState(false);
  const [gesture,   setGesture]   = useState(null);

  // ── Coordinate helpers ─────────────────────────────────────

  const toCanvas = useCallback((normX, normY) => {
    // normX/normY: 0.0–1.0 from MediaPipe
    // Mirror X so moving hand right = drawing moves right
    const x = mirror ? (1 - normX) * width : normX * width;
    const y = normY * height;
    return [x, y];
  }, [mirror, width, height]);

  const smoothed = (rawX, rawY) => {
    // Average over last SMOOTH_FRAMES positions to reduce jitter
    const h = drawState.current.history;
    h.push([rawX, rawY]);
    if (h.length > SMOOTH_FRAMES) h.shift();
    const ax = h.reduce((s, p) => s + p[0], 0) / h.length;
    const ay = h.reduce((s, p) => s + p[1], 0) / h.length;
    return [ax, ay];
  };

  // ── Render loop (runs at display framerate via rAF) ────────

  useEffect(() => {
    const disp     = dispRef.current;
    const draw     = drawRef.current;
    if (!disp || !draw) return;

    const dCtx = disp.getContext("2d");
    const pCtx = draw.getContext("2d");   // persistent drawing context
    let   rafId;

    const frame = () => {
      const { writing, x, y, visible } = handRef.current;
      const ds = drawState.current;

      // Map normalized → canvas coords + smooth
      const [rawX, rawY] = toCanvas(x, y);
      const [sx,   sy  ] = smoothed(rawX, rawY);

      // ── Update persistent draw layer ───────────────────────
      if (visible && writing) {
        if (ds.wasWriting && ds.prevX !== null) {
          // Continue stroke
          pCtx.beginPath();
          pCtx.moveTo(ds.prevX, ds.prevY);
          pCtx.lineTo(sx, sy);
          pCtx.strokeStyle = DRAW_COLOR;
          pCtx.lineWidth   = DRAW_WIDTH;
          pCtx.lineCap     = "round";
          pCtx.lineJoin    = "round";
          pCtx.stroke();
        }
        ds.prevX      = sx;
        ds.prevY      = sy;
        ds.wasWriting = true;
      } else {
        // Pen lifted — break stroke so next writing starts fresh
        ds.prevX      = null;
        ds.prevY      = null;
        ds.wasWriting = false;
      }

      // ── Compose display canvas ─────────────────────────────
      // 1. Clear
      dCtx.clearRect(0, 0, width, height);

      // 2. Blit persistent drawing layer
      dCtx.drawImage(draw, 0, 0);

      // 3. Draw cursor on top
      if (visible) {
        // Outer circle
        dCtx.beginPath();
        dCtx.arc(sx, sy, CURSOR_RADIUS, 0, Math.PI * 2);
        dCtx.fillStyle   = writing ? CURSOR_WRITING : CURSOR_IDLE;
        dCtx.fill();
        dCtx.strokeStyle = writing ? "#00ffcc" : "rgba(255,255,255,0.7)";
        dCtx.lineWidth   = 2;
        dCtx.stroke();

        // Center dot
        dCtx.beginPath();
        dCtx.arc(sx, sy, 3, 0, Math.PI * 2);
        dCtx.fillStyle = writing ? "#00ffcc" : "#fff";
        dCtx.fill();
      }

      rafId = requestAnimationFrame(frame);
    };

    rafId = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(rafId);
  }, [toCanvas, width, height]);

  // ── WebSocket connection ────────────────────────────────────

  useEffect(() => {
    let ws;
    let alive = true;

    const connect = () => {
      if (!alive) return;
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (!alive) return ws.close();
        setConnected(true);
      };

      ws.onmessage = (evt) => {
        if (!alive) return;
        const data = JSON.parse(evt.data);

        // Update shared hand ref (read by render loop)
        handRef.current = {
          writing: data.writing,
          x:       data.x,
          y:       data.y,
          visible: data.hand_visible,
          gesture: data.gesture,
        };

        // Update React state for UI (gesture label)
        if (data.gesture !== gesture) {
          setGesture(data.gesture);
          onGesture?.(data.gesture);
        }

        // Reset smoothing history when hand disappears
        if (!data.hand_visible) {
          drawState.current.history    = [];
          drawState.current.prevX      = null;
          drawState.current.prevY      = null;
          drawState.current.wasWriting = false;
        }
      };

      ws.onclose = () => {
        setConnected(false);
        // Auto-reconnect after 2s
        if (alive) setTimeout(connect, 2000);
      };

      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      alive = false;
      ws?.close();
    };
  }, [wsUrl, onGesture]);

  // ── Clear canvas handler ───────────────────────────────────

  const clearCanvas = () => {
    const pCtx = drawRef.current?.getContext("2d");
    if (pCtx) pCtx.clearRect(0, 0, width, height);
    drawState.current.prevX      = null;
    drawState.current.prevY      = null;
    drawState.current.wasWriting = false;
  };

  // ── Render ─────────────────────────────────────────────────

  const gestureColor = {
    WRITING:          "#00ffcc",
    NEXT_SLIDE:       "#ffaa00",
    PREV_SLIDE:       "#ffaa00",
    OPEN_WHITEBOARD:  "#aa88ff",
    CLOSE_WHITEBOARD: "#aa88ff",
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>

      {/* Status bar */}
      <div style={{ display: "flex", gap: 16, alignItems: "center", fontSize: 13, color: "#aaa" }}>
        <span style={{ color: connected ? "#4f4" : "#f44" }}>
          {connected ? "● Connected" : "○ Disconnected"}
        </span>
        {gesture && (
          <span style={{ color: gestureColor[gesture] ?? "#fff", fontWeight: "bold" }}>
            {gesture}
          </span>
        )}
        <button
          onClick={clearCanvas}
          style={{
            background: "#333", color: "#eee", border: "1px solid #555",
            padding: "3px 12px", borderRadius: 4, cursor: "pointer", fontSize: 12,
          }}
        >
          Clear
        </button>
      </div>

      {/* Visible display canvas */}
      <canvas
        ref={dispRef}
        width={width}
        height={height}
        style={{
          border: "2px solid #444",
          borderRadius: 8,
          background: "#1a1a1a",
          cursor: "none",
          display: "block",
        }}
      />

      {/* Hidden persistent drawing canvas (offscreen) */}
      <canvas
        ref={drawRef}
        width={width}
        height={height}
        style={{ display: "none" }}
      />
    </div>
  );
}
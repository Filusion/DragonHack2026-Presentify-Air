import { useEffect, useRef, useState, useCallback } from 'react'

const WS_URL          = 'ws://localhost:8000/ws'
const RECONNECT_BASE  = 2000    // ms — initial reconnect delay
const RECONNECT_MAX   = 15000   // ms — cap to avoid hammering a crashed server
const RECONNECT_MULT  = 1.5     // backoff multiplier

/**
 * useHandTracking
 *
 * Opens a single WebSocket to hand_server.py and exposes:
 *   handState  — continuous position / writing / gesture data (~60 fps)
 *   connected  — whether the socket is currently open
 *   onGesture  — register a callback for discrete gesture events
 *
 * BUG FIX (reconnect storm):
 *   The original code reconnected after a fixed 2 s delay, which would
 *   hammer a crashed server with rapid open/close cycles visible in the
 *   browser as connection flicker.  Exponential backoff is now applied:
 *   2 s → 3 s → 4.5 s → … → 15 s cap.  The delay resets to 2 s on a
 *   successful open so normal operation is unaffected.
 */
export function useHandTracking() {
  const [handState, setHandState] = useState({
    writing: false, x: 0.5, y: 0.5, gesture: null, hand_visible: false,
  })
  const [connected, setConnected] = useState(false)
  const gestureCallbackRef = useRef(null)
  const retryDelay         = useRef(RECONNECT_BASE)

  const onGesture = useCallback((cb) => {
    gestureCallbackRef.current = cb
  }, [])

  useEffect(() => {
    let alive = true
    let ws

    function connect() {
      if (!alive) return
      ws = new WebSocket(WS_URL)

      ws.onopen = () => {
        if (!alive) return
        setConnected(true)
        retryDelay.current = RECONNECT_BASE   // reset backoff on successful connect
      }

      ws.onmessage = (evt) => {
        if (!alive) return
        let data
        try { data = JSON.parse(evt.data) } catch { return }

        if (data.type === 'gesture_event') {
          gestureCallbackRef.current?.(data.gesture)
          return
        }

        if (data.type === 'hand_state') {
          setHandState({
            writing:      data.writing,
            x:            data.x,
            y:            data.y,
            gesture:      data.gesture,
            hand_visible: data.hand_visible,
          })
        }
      }

      ws.onclose = () => {
        setConnected(false)
        if (!alive) return
        // Exponential backoff — prevents hammering a crashed/restarting server
        const delay = retryDelay.current
        retryDelay.current = Math.min(delay * RECONNECT_MULT, RECONNECT_MAX)
        setTimeout(connect, delay)
      }

      ws.onerror = () => ws.close()
    }

    connect()
    return () => {
      alive = false
      ws?.close()
    }
  }, [])

  return { handState, connected, onGesture }
}

import { useEffect, useRef } from 'react'

const DRAW_W = 5
const DRAW_COLOR = '#81d2c7'

/**
 * HandCursor
 * Renders on top of any content. Shows a translucent circle cursor
 * that follows the index fingertip. When writing=true it also draws
 * strokes onto a persistent canvas layer.
 *
 * Props:
 *   handState    — { writing, x, y, hand_visible }
 *   mirror       — flip X axis (default true)
 *   clearTrigger — increment to wipe the drawing layer
 */
export default function HandCursor({ handState, mirror = true, clearTrigger = 0 }) {
  const dispRef = useRef(null)   // visible canvas (cursor + strokes)
  const drawRef = useRef(null)   // offscreen persistent stroke layer

  const prevRef = useRef({ x: null, y: null, writing: false })

  // Keep latest values in refs so RAF loop doesn't restart on every websocket update
  const handStateRef = useRef(handState)
  const mirrorRef = useRef(mirror)

  useEffect(() => {
    handStateRef.current = handState
  }, [handState])

  useEffect(() => {
    mirrorRef.current = mirror
  }, [mirror])

  // Clear drawing layer when requested
  useEffect(() => {
    const draw = drawRef.current
    if (!draw) return

    const ctx = draw.getContext('2d')
    const dpr = window.devicePixelRatio || 1
    const W = draw.width / dpr
    const H = draw.height / dpr

    ctx.clearRect(0, 0, W, H)
    prevRef.current = { x: null, y: null, writing: false }
  }, [clearTrigger])

  // Animation loop
  useEffect(() => {
    const disp = dispRef.current
    const draw = drawRef.current
    if (!disp || !draw) return

    const dCtx = disp.getContext('2d')
    const pCtx = draw.getContext('2d')
    let rafId

    function frame() {
      const { writing, x, y, hand_visible } = handStateRef.current

      const dpr = window.devicePixelRatio || 1
      const W = disp.width / dpr
      const H = disp.height / dpr

      // No frontend smoothing — use server coordinates directly
      const sx = mirrorRef.current ? (1 - x) * W : x * W
      const sy = y * H

      // Draw stroke on persistent layer
      const prev = prevRef.current
      if (hand_visible && writing) {
        if (prev.writing && prev.x !== null && prev.y !== null) {
          pCtx.beginPath()
          pCtx.moveTo(prev.x, prev.y)
          pCtx.lineTo(sx, sy)
          pCtx.strokeStyle = DRAW_COLOR
          pCtx.lineWidth = DRAW_W
          pCtx.lineCap = 'round'
          pCtx.lineJoin = 'round'
          pCtx.stroke()
        }
        prevRef.current = { x: sx, y: sy, writing: true }
      } else {
        prevRef.current = { x: null, y: null, writing: false }
      }

      // Compose visible canvas
      dCtx.clearRect(0, 0, W, H)
      dCtx.drawImage(draw, 0, 0, W, H)

      if (hand_visible) {
        const r = 18

        dCtx.beginPath()
        dCtx.arc(sx, sy, r, 0, Math.PI * 2)
        dCtx.fillStyle = writing
          ? 'rgba(129,210,199,0.5)'
          : 'rgba(255,255,255,0.28)'
        dCtx.fill()
        dCtx.strokeStyle = writing
          ? '#81d2c7'
          : 'rgba(255,255,255,0.55)'
        dCtx.lineWidth = 2
        dCtx.stroke()

        dCtx.beginPath()
        dCtx.arc(sx, sy, 3, 0, Math.PI * 2)
        dCtx.fillStyle = writing ? '#81d2c7' : '#fff'
        dCtx.fill()
      }

      rafId = requestAnimationFrame(frame)
    }

    rafId = requestAnimationFrame(frame)
    return () => cancelAnimationFrame(rafId)
  }, [])

  // Match canvas size to parent
  useEffect(() => {
    const disp = dispRef.current
    const draw = drawRef.current
    if (!disp || !draw || !disp.parentElement) return

    function resize() {
      const { width, height } = disp.parentElement.getBoundingClientRect()
      const dpr = window.devicePixelRatio || 1

      ;[disp, draw].forEach((canvas) => {
        canvas.width = Math.floor(width * dpr)
        canvas.height = Math.floor(height * dpr)

        const ctx = canvas.getContext('2d')
        ctx.setTransform(1, 0, 0, 1, 0, 0)
        ctx.scale(dpr, dpr)
      })
    }

    const ro = new ResizeObserver(resize)
    ro.observe(disp.parentElement)
    resize()

    return () => ro.disconnect()
  }, [])

  return (
    <>
      <canvas ref={drawRef} style={{ display: 'none' }} />
      <canvas
        ref={dispRef}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
          zIndex: 50,
        }}
      />
    </>
  )
}
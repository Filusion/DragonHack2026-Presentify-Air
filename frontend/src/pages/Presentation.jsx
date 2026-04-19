import React, { useEffect, useRef, useState, useCallback } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import HandCursor from '../components/HandCursor'
import { useHandTracking } from '../hooks/useHandTracking'

const WB_COLORS = [
  { hex: '#81d2c7', label: 'Teal' },
  { hex: '#ffffff', label: 'White' },
  { hex: '#ffd166', label: 'Yellow' },
  { hex: '#ef9f27', label: 'Amber' },
  { hex: '#ff6b6b', label: 'Red' },
  { hex: '#416788', label: 'Blue' },
]

// ─── Pitch deck slides (unchanged) ───────────────────────────
function Slide1() {
  return (
    <div style={{ position:'relative', width:'100%', aspectRatio:'16/9', background:'#0f1825', overflow:'hidden', fontFamily:"'DM Sans',system-ui,sans-serif", borderRadius:8 }}>
      <div style={{ position:'absolute', width:500, height:500, borderRadius:'50%', background:'radial-gradient(circle, rgba(65,103,136,0.35) 0%, transparent 70%)', top:'-10%', right:'-5%' }} />
      <div style={{ position:'absolute', width:300, height:300, borderRadius:'50%', background:'radial-gradient(circle, rgba(129,210,199,0.2) 0%, transparent 70%)', bottom:'5%', left:'5%' }} />
      <div style={{ position:'absolute', top:0, left:0, right:0, height:4, background:'linear-gradient(90deg,#416788,#81d2c7)' }} />
      <div style={{ position:'absolute', inset:0, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:'clamp(8px,2vw,20px)' }}>
        <div style={{ display:'flex', alignItems:'center', gap:'clamp(8px,1.5vw,16px)', marginBottom:'clamp(4px,1vw,10px)' }}>
          <div style={{ width:'clamp(8px,1.2vw,14px)', height:'clamp(8px,1.2vw,14px)', borderRadius:'50%', background:'#81d2c7' }} />
          <span style={{ fontSize:'clamp(10px,1.2vw,14px)', fontWeight:600, letterSpacing:'0.2em', textTransform:'uppercase', color:'#81d2c7' }}>Introducing</span>
        </div>
        <h1 style={{ fontSize:'clamp(28px,6vw,80px)', fontFamily:"'DM Serif Display',Georgia,serif", color:'#fff', margin:0, letterSpacing:'-0.02em', textAlign:'center', lineHeight:1.05 }}>Presentify Air</h1>
        <p style={{ fontSize:'clamp(10px,1.4vw,18px)', color:'rgba(255,255,255,0.45)', margin:0, letterSpacing:'0.08em', textTransform:'uppercase' }}>Present smarter. Move freely.</p>
      </div>
      <div style={{ position:'absolute', bottom:16, right:20, fontSize:'clamp(9px,1vw,12px)', color:'rgba(255,255,255,0.2)', fontWeight:500 }}>01 / 05</div>
    </div>
  )
}
function Slide2() {
  return (
    <div style={{ position:'relative', width:'100%', aspectRatio:'16/9', background:'#f7f9fc', overflow:'hidden', fontFamily:"'DM Sans',system-ui,sans-serif", borderRadius:8 }}>
      <div style={{ position:'absolute', top:0, left:0, right:0, height:4, background:'linear-gradient(90deg,#416788,#81d2c7)' }} />
      <div style={{ position:'absolute', inset:0, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', padding:'6% 10%', gap:'clamp(8px,2vw,24px)', textAlign:'center' }}>
        <span style={{ fontSize:'clamp(9px,1vw,12px)', fontWeight:600, letterSpacing:'0.15em', textTransform:'uppercase', color:'#7389ae' }}>The Problem</span>
        <h2 style={{ fontSize:'clamp(18px,3.8vw,52px)', fontFamily:"'DM Serif Display',Georgia,serif", color:'#1a2332', margin:0, lineHeight:1.1 }}>Presenting hasn't changed<br /><span style={{ color:'#416788' }}>in 30 years.</span></h2>
        <p style={{ fontSize:'clamp(10px,1.4vw,18px)', color:'#5a6a7e', maxWidth:'70%', lineHeight:1.6, margin:0 }}>Clickers, cables, clicking through slides — presenters are still tethered to a podium. Presentify Air is the future of presenting: control your slides with nothing but your hands.</p>
        <div style={{ display:'flex', gap:'clamp(8px,2vw,24px)', marginTop:'clamp(4px,1vw,10px)' }}>
          {['No clicker needed','No cables','Full freedom of movement'].map(t => (
            <div key={t} style={{ display:'flex', alignItems:'center', gap:8, fontSize:'clamp(9px,1.1vw,14px)', fontWeight:500, color:'#416788' }}>
              <div style={{ width:'clamp(6px,0.8vw,10px)', height:'clamp(6px,0.8vw,10px)', borderRadius:'50%', background:'#81d2c7', flexShrink:0 }} />{t}
            </div>
          ))}
        </div>
      </div>
      <div style={{ position:'absolute', bottom:16, right:20, fontSize:'clamp(9px,1vw,12px)', color:'#b5bad0', fontWeight:500 }}>02 / 05</div>
    </div>
  )
}
function Slide3() {
  const features = [
    { icon:'✋', title:'Hand Gestures', desc:'Navigate slides with intuitive hand movements — swipe, point, pinch.' },
    { icon:'🖊', title:'Live Whiteboard', desc:'Draw and annotate directly over your slides in real time.' },
    { icon:'📁', title:'Upload Any Deck', desc:'Drop in your .pptx and present instantly — no conversion needed.' },
    { icon:'🎨', title:'Clean Design', desc:'Bento-style dashboard. Distraction-free presentation mode.' },
  ]
  return (
    <div style={{ position:'relative', width:'100%', aspectRatio:'16/9', background:'#0f1825', overflow:'hidden', fontFamily:"'DM Sans',system-ui,sans-serif", borderRadius:8 }}>
      <div style={{ position:'absolute', top:0, left:0, right:0, height:4, background:'linear-gradient(90deg,#416788,#81d2c7)' }} />
      <div style={{ position:'absolute', inset:'5% 5% 10%', display:'flex', flexDirection:'column', gap:'clamp(6px,1.5vw,16px)' }}>
        <div>
          <span style={{ fontSize:'clamp(9px,1vw,12px)', fontWeight:600, letterSpacing:'0.15em', textTransform:'uppercase', color:'#81d2c7' }}>Core Features</span>
          <h2 style={{ fontSize:'clamp(16px,2.8vw,36px)', fontFamily:"'DM Serif Display',Georgia,serif", color:'#fff', margin:'4px 0 0', lineHeight:1.1 }}>Everything you need to present.</h2>
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'clamp(6px,1.2vw,14px)', flex:1 }}>
          {features.map(f => (
            <div key={f.title} style={{ background:'rgba(255,255,255,0.05)', border:'1px solid rgba(255,255,255,0.08)', borderRadius:12, padding:'clamp(8px,1.5vw,18px)', display:'flex', flexDirection:'column', gap:'clamp(4px,0.8vw,8px)' }}>
              <span style={{ fontSize:'clamp(14px,2vw,26px)' }}>{f.icon}</span>
              <div style={{ fontSize:'clamp(10px,1.2vw,15px)', fontWeight:600, color:'#fff' }}>{f.title}</div>
              <div style={{ fontSize:'clamp(8px,1vw,13px)', color:'rgba(255,255,255,0.45)', lineHeight:1.4 }}>{f.desc}</div>
            </div>
          ))}
        </div>
      </div>
      <div style={{ position:'absolute', bottom:16, right:20, fontSize:'clamp(9px,1vw,12px)', color:'rgba(255,255,255,0.2)', fontWeight:500 }}>03 / 05</div>
    </div>
  )
}
function Slide4() {
  const steps = [
    { n:'01', label:'Upload', desc:'Drop your .pptx into the Bento dashboard' },
    { n:'02', label:'Open Camera', desc:'Presentify Air detects your hand in real time' },
    { n:'03', label:'Present', desc:'Swipe left or right to navigate slides' },
    { n:'04', label:'Annotate', desc:'Switch to whiteboard mode to draw live' },
  ]
  return (
    <div style={{ position:'relative', width:'100%', aspectRatio:'16/9', background:'#f7f9fc', overflow:'hidden', fontFamily:"'DM Sans',system-ui,sans-serif", borderRadius:8 }}>
      <div style={{ position:'absolute', top:0, left:0, right:0, height:4, background:'linear-gradient(90deg,#416788,#81d2c7)' }} />
      <div style={{ position:'absolute', inset:'5% 5% 10%', display:'flex', flexDirection:'column', gap:'clamp(6px,1.5vw,16px)' }}>
        <div>
          <span style={{ fontSize:'clamp(9px,1vw,12px)', fontWeight:600, letterSpacing:'0.15em', textTransform:'uppercase', color:'#7389ae' }}>How It Works</span>
          <h2 style={{ fontSize:'clamp(16px,2.8vw,36px)', fontFamily:"'DM Serif Display',Georgia,serif", color:'#1a2332', margin:'4px 0 0', lineHeight:1.1 }}>Four steps to a better presentation.</h2>
        </div>
        <div style={{ display:'flex', gap:'clamp(6px,1.2vw,14px)', flex:1, alignItems:'stretch' }}>
          {steps.map((s,i) => (
            <div key={s.n} style={{ flex:1, background:'#fff', border:'1px solid rgba(65,103,136,0.12)', borderRadius:12, padding:'clamp(8px,1.5vw,18px)', display:'flex', flexDirection:'column', gap:'clamp(4px,0.8vw,10px)', position:'relative', overflow:'hidden' }}>
              <div style={{ position:'absolute', top:0, left:0, right:0, height:3, background:[,'#416788','#7389ae','#81d2c7','#b5bad0'][i+1] }} />
              <span style={{ fontSize:'clamp(16px,2.5vw,32px)', fontFamily:"'DM Serif Display',Georgia,serif", color:'rgba(65,103,136,0.2)', fontWeight:700, lineHeight:1 }}>{s.n}</span>
              <div style={{ fontSize:'clamp(10px,1.2vw,15px)', fontWeight:600, color:'#1a2332' }}>{s.label}</div>
              <div style={{ fontSize:'clamp(8px,1vw,13px)', color:'#5a6a7e', lineHeight:1.4 }}>{s.desc}</div>
            </div>
          ))}
        </div>
      </div>
      <div style={{ position:'absolute', bottom:16, right:20, fontSize:'clamp(9px,1vw,12px)', color:'#b5bad0', fontWeight:500 }}>04 / 05</div>
    </div>
  )
}
function Slide5() {
  return (
    <div style={{ position:'relative', width:'100%', aspectRatio:'16/9', background:'#0f1825', overflow:'hidden', fontFamily:"'DM Sans',system-ui,sans-serif", borderRadius:8 }}>
      <div style={{ position:'absolute', width:600, height:600, borderRadius:'50%', background:'radial-gradient(circle, rgba(65,103,136,0.3) 0%, transparent 65%)', top:'-20%', left:'-10%' }} />
      <div style={{ position:'absolute', width:400, height:400, borderRadius:'50%', background:'radial-gradient(circle, rgba(129,210,199,0.2) 0%, transparent 65%)', bottom:'-15%', right:'5%' }} />
      <div style={{ position:'absolute', top:0, left:0, right:0, height:4, background:'linear-gradient(90deg,#416788,#81d2c7)' }} />
      <div style={{ position:'absolute', inset:0, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:'clamp(8px,2vw,20px)', padding:'0 10%', textAlign:'center' }}>
        <span style={{ fontSize:'clamp(9px,1vw,12px)', fontWeight:600, letterSpacing:'0.15em', textTransform:'uppercase', color:'#81d2c7' }}>The Vision</span>
        <h2 style={{ fontSize:'clamp(20px,4.5vw,60px)', fontFamily:"'DM Serif Display',Georgia,serif", color:'#fff', margin:0, lineHeight:1.1 }}>The stage is yours.<br /><span style={{ color:'#81d2c7' }}>No strings attached.</span></h2>
        <p style={{ fontSize:'clamp(10px,1.3vw,17px)', color:'rgba(255,255,255,0.45)', maxWidth:'65%', lineHeight:1.65, margin:0 }}>Presentify Air removes every barrier between you and your audience. Walk the stage, own the room, and let your hands do the talking.</p>
        <div style={{ marginTop:'clamp(4px,1vw,12px)', padding:'clamp(8px,1.2vw,14px) clamp(16px,2.5vw,32px)', background:'linear-gradient(135deg,#416788,#7389ae)', borderRadius:999, fontSize:'clamp(10px,1.2vw,15px)', fontWeight:600, color:'#fff', letterSpacing:'0.04em' }}>presentifyair.com</div>
      </div>
      <div style={{ position:'absolute', bottom:16, right:20, fontSize:'clamp(9px,1vw,12px)', color:'rgba(255,255,255,0.2)', fontWeight:500 }}>05 / 05</div>
    </div>
  )
}

const PITCH_DECK = [
  { id:'pitch-1', component:Slide1, title:'Presentify Air' },
  { id:'pitch-2', component:Slide2, title:'The Future of Presenting' },
  { id:'pitch-3', component:Slide3, title:'Core Features' },
  { id:'pitch-4', component:Slide4, title:'How It Works' },
  { id:'pitch-5', component:Slide5, title:'The Vision' },
]

// ─── PPTX slide renderers (unchanged) ────────────────────────
function Run({ r }) {
  return <span style={{ fontWeight:r.bold?700:undefined, fontStyle:r.italic?'italic':undefined, fontSize:r.fontSize?`${r.fontSize}px`:undefined, color:r.color||undefined }}>{r.text}</span>
}
function Para({ para }) {
  const alignMap = { l:'left', r:'right', ctr:'center', just:'justify' }
  const align = alignMap[para.align] || 'left'
  const bullet = para.bulletChar || (para.bullet ? '•' : null)
  const indent = para.level * 14
  return (
    <div style={{ display:'flex', gap:5, paddingLeft:indent, textAlign:align, marginBottom:2, lineHeight:1.35 }}>
      {bullet && <span style={{ flexShrink:0, opacity:0.6, minWidth:12 }}>{bullet}</span>}
      <span style={{ flex:1 }}>{para.runs.map((r,i) => <Run key={i} r={r} />)}</span>
    </div>
  )
}
function TextShape({ shape }) {
  if (!shape.pos) return null
  const { x, y, w, h } = shape.pos
  if (x > 100 || y > 100 || x < -20 || y < -20) return null
  return (
    <div style={{ position:'absolute', left:`${Math.max(0,x)}%`, top:`${Math.max(0,y)}%`, width:`${Math.min(w,100-Math.max(0,x))}%`, minHeight:`${h}%`, overflow:'hidden', padding:'2px 4px', boxSizing:'border-box' }}>
      {shape.paras.map((p,i) => <Para key={i} para={p} />)}
    </div>
  )
}
function SlideImage({ img }) {
  if (!img.pos) return null
  const { x, y, w, h } = img.pos
  if (x > 100 || y > 100) return null
  return <img src={img.dataUrl} alt="" style={{ position:'absolute', left:`${Math.max(0,x)}%`, top:`${Math.max(0,y)}%`, width:`${Math.min(w,100-Math.max(0,x))}%`, height:`${Math.min(h,100-Math.max(0,y))}%`, objectFit:'contain', pointerEvents:'none' }} />
}
function SlideTable({ table }) {
  return (
    <div style={{ position:'absolute', inset:'5%', display:'flex', alignItems:'center', justifyContent:'center', overflow:'auto' }}>
      <table style={{ borderCollapse:'collapse', width:'100%', fontSize:'clamp(9px,1.3vw,15px)' }}>
        <tbody>{table.rows.map((row,ri) => (
          <tr key={ri}>{row.map((cellParas,ci) => (
            <td key={ci} style={{ border:'1px solid rgba(65,103,136,0.3)', padding:'5px 8px', background:ri===0?'rgba(65,103,136,0.1)':ci===0?'rgba(65,103,136,0.05)':'transparent', fontWeight:ri===0?600:400, verticalAlign:'top' }}>
              {cellParas.map((p,pi) => <Para key={pi} para={p} />)}
            </td>
          ))}</tr>
        ))}</tbody>
      </table>
    </div>
  )
}
function SlideView({ slide }) {
  const bg = slide.bg || '#ffffff'
  const hasTable = slide.tables?.length > 0
  return (
    <div style={{ position:'relative', width:'100%', aspectRatio:'16/9', background:bg, borderRadius:8, overflow:'hidden', fontFamily:"'DM Sans',system-ui,sans-serif", fontSize:'clamp(10px,1.5vw,18px)', color:'#1a2332' }}>
      <div style={{ position:'absolute', top:0, left:0, right:0, height:4, background:'linear-gradient(90deg,#416788,#81d2c7)', zIndex:10 }} />
      {slide.images?.map((img,i) => <SlideImage key={i} img={img} />)}
      {hasTable && slide.tables.map((t,i) => <SlideTable key={i} table={t} />)}
      {!hasTable && slide.shapes?.map((s,i) => <TextShape key={i} shape={s} />)}
      {hasTable && slide.shapes?.filter(s => s.type==='title').map((s,i) => <TextShape key={i} shape={s} />)}
    </div>
  )
}

// ─── Gesture toast ────────────────────────────────────────────
function GestureToast({ gesture }) {
  const labels = {
    NEXT_SLIDE:       '→ Next Slide',
    PREV_SLIDE:       '← Prev Slide',
    OPEN_WHITEBOARD:  '✌️ Whiteboard Open',
    CLOSE_WHITEBOARD: '👍 Whiteboard Closed',
    WRITING:          '🖊 Drawing',
  }
  if (!gesture) return null
  return (
    <div style={{
      position:'fixed', bottom:90, left:'50%', transform:'translateX(-50%)',
      background:'rgba(15,24,37,0.92)', color:'#81d2c7',
      padding:'10px 24px', borderRadius:999,
      fontSize:15, fontWeight:600, letterSpacing:'0.04em',
      border:'1px solid rgba(129,210,199,0.3)',
      backdropFilter:'blur(8px)', zIndex:200,
      pointerEvents:'none',
      animation:'fadeInUp 0.2s ease',
    }}>
      {labels[gesture] || gesture}
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────
export default function Presentation() {
  const { id }   = useParams()
  const navigate = useNavigate()
  const location = useLocation()

  const passedSlides = location.state?.slides
  const isPitch = location.state?.isPitch
  const slides = isPitch ? PITCH_DECK : (passedSlides?.length > 0 ? passedSlides : PITCH_DECK)

  const [mode,        setMode]        = useState('slide')
  const [slideIndex,  setSlideIndex]  = useState(0)
  const [brushColor,  setBrushColor]  = useState('#81d2c7')
  const [brushSize,   setBrushSize]   = useState(4)
  const [clearCount,  setClearCount]  = useState(0)
  const [toastGesture, setToastGesture] = useState(null)
  const toastTimer = useRef(null)

  // Mouse/touch drawing (whiteboard only)
  const canvasRef = useRef(null)
  const drawing   = useRef(false)
  const lastPoint = useRef(null)

  // Hand tracking
  const { handState, connected, onGesture } = useHandTracking()

  // Show a brief toast when a gesture fires
  const showToast = useCallback((g) => {
    setToastGesture(g)
    clearTimeout(toastTimer.current)
    toastTimer.current = setTimeout(() => setToastGesture(null), 1500)
  }, [])

  // Keep slides.length in a ref so the gesture callback never goes stale
  // without re-registering — avoids the effect re-running on every render.
  const slidesLengthRef = useRef(slides.length)
  useEffect(() => { slidesLengthRef.current = slides.length }, [slides.length])

  // Wire up gesture events — empty dep array so this runs exactly once.
  // All values accessed inside come from refs or stable setters.
  useEffect(() => {
    onGesture((gesture) => {
      showToast(gesture)
      if (gesture === 'NEXT_SLIDE') {
        setSlideIndex(i => Math.min(i + 1, slidesLengthRef.current - 1))
      } else if (gesture === 'PREV_SLIDE') {
        setSlideIndex(i => Math.max(i - 1, 0))
      } else if (gesture === 'OPEN_WHITEBOARD') {
        setMode('whiteboard')
      } else if (gesture === 'CLOSE_WHITEBOARD') {
        setMode('slide')
      }
    })
  }, [onGesture, showToast])  // stable refs — does not re-run on slide change

  // Keyboard shortcuts
  useEffect(() => {
    function handleKey(e) {
      if      (e.key === 'ArrowRight' || e.key === ' ') setSlideIndex(i => Math.min(i + 1, slides.length - 1))
      else if (e.key === 'ArrowLeft')                   setSlideIndex(i => Math.max(i - 1, 0))
      else if (e.key === 'w')                           setMode(m => m === 'slide' ? 'whiteboard' : 'slide')
      else if (e.key === 'Escape')                      navigate('/')
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [navigate, slides.length])

  // Whiteboard canvas resize
  // FIX: ctx.scale() is multiplicative — calling it on every resize event without
  // resetting the transform first multiplies the scale by dpr each time, shifting
  // every drawn point further off-screen with each window resize.
  // Always call ctx.setTransform(1,0,0,1,0,0) to reset before re-applying scale.
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    function resize() {
      const { width, height } = canvas.getBoundingClientRect()
      const dpr = window.devicePixelRatio || 1
      canvas.width  = Math.floor(width  * dpr)
      canvas.height = Math.floor(height * dpr)
      const ctx = canvas.getContext('2d')
      ctx.setTransform(1, 0, 0, 1, 0, 0)   // reset before scaling
      ctx.scale(dpr, dpr)
    }
    resize()
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [mode])

  function getPoint(e) {
    const rect = canvasRef.current.getBoundingClientRect()
    return { x:(e.clientX??e.touches?.[0]?.clientX)-rect.left, y:(e.clientY??e.touches?.[0]?.clientY)-rect.top }
  }
  function startDraw(e) { drawing.current=true; lastPoint.current=getPoint(e) }
  function endDraw()    { drawing.current=false; lastPoint.current=null }
  function draw(e) {
    if (!drawing.current) return
    const ctx = canvasRef.current.getContext('2d')
    const p = getPoint(e)
    ctx.strokeStyle=brushColor; ctx.lineWidth=brushSize; ctx.lineCap='round'; ctx.lineJoin='round'
    ctx.beginPath(); ctx.moveTo(lastPoint.current.x,lastPoint.current.y); ctx.lineTo(p.x,p.y); ctx.stroke()
    lastPoint.current=p
  }
  function clearCanvas() {
    const canvas = canvasRef.current
    if (canvas) canvas.getContext('2d').clearRect(0,0,canvas.width,canvas.height)
    setClearCount(n => n + 1)   // also clears hand cursor strokes
  }

  const currentSlide  = slides[slideIndex]
  const isPitchSlide  = !!currentSlide?.component

  return (
    <div className="presentation-fullscreen">
      {/* ── Toolbar ── */}
      <div className="pres-toolbar">
        <div className="pres-toolbar-left">
          <button className="tb-btn exit" onClick={() => navigate('/')}>← Exit</button>
        </div>

        <div className="pres-toolbar-center">
          <button className={`tb-btn ${mode==='slide' ? 'active':''}`} onClick={() => setMode('slide')}>Slides</button>
          <button className={`tb-btn ${mode==='whiteboard' ? 'active':''}`} onClick={() => setMode('whiteboard')}>Whiteboard</button>
          {mode === 'slide' && <>
            <div style={{ width:1, height:20, background:'rgba(255,255,255,0.1)', margin:'0 4px' }} />
            <button className="tb-btn" onClick={() => setSlideIndex(i => Math.max(i-1,0))}>←</button>
            <span className="slide-counter">{slideIndex+1} / {slides.length}</span>
            <button className="tb-btn" onClick={() => setSlideIndex(i => Math.min(i+1,slides.length-1))}>→</button>
          </>}
        </div>

        <div className="pres-toolbar-right">
          {/* Hand tracking indicator */}
          <div style={{ display:'flex', alignItems:'center', gap:6, fontSize:12, color: connected ? '#81d2c7' : 'rgba(255,255,255,0.3)' }}>
            <div style={{ width:8, height:8, borderRadius:'50%', background: connected ? '#81d2c7' : 'rgba(255,255,255,0.2)' }} />
            {connected ? (handState.hand_visible ? '✋ Hand detected' : 'Hand tracker on') : 'No hand tracker'}
          </div>

          {mode === 'whiteboard' && <>
            <div style={{ width:1, height:20, background:'rgba(255,255,255,0.1)', margin:'0 8px' }} />
            <select value={brushSize} onChange={e => setBrushSize(Number(e.target.value))}
              style={{ background:'rgba(255,255,255,0.08)', border:'1px solid rgba(255,255,255,0.12)', color:'rgba(255,255,255,0.8)', borderRadius:8, padding:'6px 10px', fontSize:13, fontFamily:'inherit', cursor:'pointer' }}>
              <option value={2}>Thin</option>
              <option value={4}>Medium</option>
              <option value={8}>Thick</option>
            </select>
            <button className="tb-btn" onClick={clearCanvas}>Clear</button>
          </>}

          <span style={{ fontSize:12, color:'rgba(255,255,255,0.25)', paddingLeft:8 }}>
            {mode==='slide' ? '← → navigate · W whiteboard · Esc exit' : 'W for slides · Esc exit'}
          </span>
        </div>
      </div>

      {/* ── Content ── */}
      <div className="pres-content">
        {mode === 'slide' ? (
          <div style={{ position:'relative', width:'100%', maxWidth:960 }}>
            {isPitchSlide ? <currentSlide.component /> : <SlideView slide={currentSlide} />}
            {/* Hand cursor overlay on slide */}
            <HandCursor
              handState={handState}
              mirror={true}
              clearTrigger={clearCount}
            />
          </div>
        ) : (
          <div className="whiteboard-wrapper" style={{ position:'relative' }}>
            {/* Mouse drawing canvas */}
            <canvas ref={canvasRef} className="whiteboard-canvas"
              onPointerDown={startDraw} onPointerMove={draw}
              onPointerUp={endDraw} onPointerCancel={endDraw} onPointerLeave={endDraw} />

            {/* Hand cursor + drawing overlay */}
            <HandCursor
              handState={handState}
              mirror={true}
              clearTrigger={clearCount}
            />

            <div className="wb-tools">
              {WB_COLORS.map(c => (
                <div key={c.hex} className={`wb-color ${brushColor===c.hex?'selected':''}`}
                  style={{ background:c.hex }} title={c.label} onClick={() => setBrushColor(c.hex)} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Gesture toast ── */}
      <GestureToast gesture={toastGesture} />

      {/* ── Gesture cheat sheet (bottom-left) ── */}
      {connected && (
        <div style={{
          position:'fixed', bottom:20, left:20,
          background:'rgba(15,24,37,0.85)', borderRadius:12,
          padding:'10px 16px', fontSize:11,
          color:'rgba(255,255,255,0.45)', lineHeight:1.8,
          border:'1px solid rgba(65,103,136,0.2)',
          backdropFilter:'blur(8px)', zIndex:100,
        }}>
          <div style={{ color:'rgba(129,210,199,0.7)', fontWeight:600, marginBottom:4 }}>Hand Gestures</div>
          <div>🖐️ Open palm + swipe → slide</div>
          <div>✌️ Victory sign → whiteboard</div>
          <div>👍 Thumb up → slides</div>
          <div>🖊 Pinch → draw</div>
        </div>
      )}

      <style>{`
        @keyframes fadeInUp {
          from { opacity:0; transform:translateX(-50%) translateY(8px); }
          to   { opacity:1; transform:translateX(-50%) translateY(0); }
        }
      `}</style>
    </div>
  )
}

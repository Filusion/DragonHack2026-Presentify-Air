import React, { useState, useRef } from 'react'
import PresentationCard from '../components/PresentationCard'
import { useNavigate } from 'react-router-dom'
import { parsePptx } from '../utils/parsePptx'

export default function Dashboard() {
  const [presentations, setPresentations] = useState([
    { id: 'pitch', title: 'Presentify Air — Pitch Deck', slides: 5, parsedSlides: null, isPitch: true },
    { id: '1', title: 'My First Presentation', slides: 8, parsedSlides: null },
    { id: '2', title: 'Project Deck', slides: 12, parsedSlides: null },
  ])
  const [dragOver, setDragOver] = useState(false)
  const [parsing, setParsing] = useState(false)
  const fileInputRef = useRef(null)
  const navigate = useNavigate()

  async function processFile(file) {
    if (!file) return
    const isPptx = file.name.toLowerCase().endsWith('.pptx')

    if (isPptx) {
      setParsing(true)
      try {
        const { title, slides } = await parsePptx(file)
        const newPres = {
          id: String(Date.now()),
          title,
          slides: slides.length,
          parsedSlides: slides,
        }
        setPresentations(prev => [newPres, ...prev])
      } catch (err) {
        console.error('Failed to parse pptx:', err)
        // fallback: add without parsed slides
        const newPres = { id: String(Date.now()), title: file.name.replace(/\.[^/.]+$/, ''), slides: 0, parsedSlides: null }
        setPresentations(prev => [newPres, ...prev])
      } finally {
        setParsing(false)
      }
    } else {
      // PDF or .ppt — can't parse in browser, add as stub
      const newPres = { id: String(Date.now()), title: file.name.replace(/\.[^/.]+$/, ''), slides: 0, parsedSlides: null }
      setPresentations(prev => [newPres, ...prev])
    }
  }

  function handleUpload(e) {
    processFile(e.target.files?.[0])
  }

  function handleDrop(e) {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(false)
    processFile(e.dataTransfer.files?.[0])
  }

  function handleCreateNew() {
    const newId = String(Date.now())
    const newPres = { id: newId, title: 'Untitled Presentation', slides: 0, parsedSlides: null }
    setPresentations(prev => [newPres, ...prev])
    navigate(`/presentation/${newId}`, { state: { slides: null, title: 'Untitled Presentation' } })
  }

  function handleStartPresenting(p) {
    navigate(`/presentation/${p.id}`, { state: { slides: p.parsedSlides, title: p.title, isPitch: p.isPitch || false } })
  }

  return (
    <main className="dashboard">
      <div className="dash-header">
        <div className="dash-eyebrow">Workspace</div>
      </div>

      <div className={`bento-grid ${dragOver ? 'drag-over' : ''}`}>

        {/* Upload tile */}
        <label
          className="bento-cell tile-upload"
          onDragEnter={e => { e.preventDefault(); e.stopPropagation(); setDragOver(true) }}
          onDragOver={e  => { e.preventDefault(); e.stopPropagation(); setDragOver(true) }}
          onDragLeave={e => { e.preventDefault(); e.stopPropagation(); setDragOver(false) }}
          onDrop={handleDrop}
        >
          <span className="tile-bubble tile-bubble-1" />
          <span className="tile-bubble tile-bubble-2" />
          <span className="tile-bubble tile-bubble-3" />
          <div className="tile-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="#416788" strokeWidth="1.5">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <div>
            <div className="tile-label">{parsing ? 'Parsing slides…' : 'Upload Presentation'}</div>
            <div className="tile-desc">{parsing ? 'Extracting slide content' : 'Drop a .pptx here, or click to browse'}</div>
          </div>
          <input ref={fileInputRef} type="file" accept=".ppt,.pptx,.pdf" onChange={handleUpload} />
        </label>

        {/* Create new tile */}
        <div className="bento-cell tile-create" onClick={handleCreateNew} style={{ cursor: 'pointer' }}>
          <span className="tile-bubble tile-bubble-1" />
          <span className="tile-bubble tile-bubble-2" />
          <span className="tile-bubble tile-bubble-3" />
          <div className="tile-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="#0f6e56" strokeWidth="1.5">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <line x1="12" y1="8" x2="12" y2="16"/>
              <line x1="8" y1="12" x2="16" y2="12"/>
            </svg>
          </div>
          <div>
            <div className="tile-label" style={{ color: '#085041' }}>Create New</div>
            <div className="tile-desc" style={{ color: '#0f6e56' }}>Start from a blank canvas</div>
          </div>
        </div>

        {/* Stats tile */}
        <div className="bento-cell tile-stats">
          <div className="stat-chip">
            <span className="stat-n">{presentations.length}</span>
            <span className="stat-l">Total</span>
          </div>
          <div className="stat-chip">
            <span className="stat-n">{presentations.reduce((a, p) => a + p.slides, 0)}</span>
            <span className="stat-l">Slides</span>
          </div>
          <div className="stat-chip">
            <span className="stat-n">{presentations.filter(p => p.parsedSlides).length}</span>
            <span className="stat-l">Uploaded</span>
          </div>
          <div className="stat-chip">
            <span className="stat-n" style={{ color: '#0f6e56' }}>
              {presentations.length > 0 ? Math.round(presentations.reduce((a, p) => a + p.slides, 0) / presentations.length) : 0}
            </span>
            <span className="stat-l">Avg Slides</span>
          </div>
        </div>

        {/* Section divider */}
        <div style={{ gridColumn: 'span 12', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 0' }}>
          <span className="section-label">All Presentations</span>
          <span className="section-label" style={{ color: '#b5bad0' }}>{presentations.length} items</span>
        </div>

        {/* Presentation cards */}
        {presentations.length === 0 ? (
          <div className="bento-cell empty-bento">
            <p>No presentations yet — upload one or create a new one above.</p>
          </div>
        ) : (
          presentations.map(p => (
            <PresentationCard
              key={p.id}
              presentation={p}
              onStart={() => handleStartPresenting(p)}
            />
          ))
        )}
      </div>
    </main>
  )
}
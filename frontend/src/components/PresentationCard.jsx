import React from 'react'

export default function PresentationCard({ presentation, onStart }) {
  return (
    <div className="bento-cell pres-card" onClick={onStart}>
      <div className="pres-card-thumb">
        <svg className="pres-thumb-icon" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#416788" strokeWidth="1.5">
          <rect x="2" y="3" width="20" height="14" rx="2"/>
          <path d="M8 21h8M12 17v4"/>
        </svg>
      </div>
      <div className="pres-card-body">
        <div className="pres-card-title">{presentation.title}</div>
        <div className="pres-card-meta">{presentation.slides} slides</div>
      </div>
      <div className="pres-card-footer">
        <span className="badge">{presentation.slides} slides</span>
        <button
          className="start-btn"
          onClick={e => { e.stopPropagation(); onStart(); }}
        >
          Present →
        </button>
      </div>
    </div>
  )
}

import React from 'react'
import { Link, useNavigate } from 'react-router-dom'

export default function Header() {
  const navigate = useNavigate()

  return (
    <header className="header">
      <Link to="/" className="logo" aria-label="Go to dashboard">
        <span className="logo-next-label">Next slide</span>
        <span className="logo-text">Presentify Air</span>
      </Link>

      <nav className="nav">
        <button
          className="account-btn"
          onClick={() => navigate('/account')}
          aria-label="Account"
          title="My Account"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="8" r="4"/>
            <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
          </svg>
          <span className="account-btn-label">Account</span>
        </button>
      </nav>
    </header>
  )
}
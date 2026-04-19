import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Presentation from './pages/Presentation'
import Header from './components/Header'

// NOTE: The main-backend WebSocket (session_snapshot / timeline_update) has been
// intentionally removed from App.jsx.
//
// It was opening a *second* connection to the same ws://localhost:8000/ws endpoint
// already used by useHandTracking(), doubling server-side client count and causing
// reconnect storms whenever hand_server.py restarted.
//
// All real-time data (hand_state, gesture_event) flows exclusively through
// useHandTracking.js.  If a separate session WebSocket is needed in future,
// connect it to a *different* path (e.g. /ws/session) to keep streams independent.

export default function App() {
  return (
    <div className="app-root">
      <Header />
      <Routes>
        <Route path="/"                    element={<Dashboard />}      />
        <Route path="/presentation/:id"    element={<Presentation />}   />
        <Route path="/presentation"        element={<Presentation />}   />
      </Routes>
    </div>
  )
}

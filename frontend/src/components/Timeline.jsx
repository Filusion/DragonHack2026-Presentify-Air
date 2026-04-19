import React from "react";

function formatTimestamp(timestamp) {
  if (!timestamp) {
    return "Unknown time";
  }

  return new Date(timestamp * 1000).toLocaleTimeString();
}

export default function Timeline({ events }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Timeline</h2>
        <p>Live backend events</p>
      </div>

      <ul className="timeline">
        {events.length === 0 ? (
          <li className="timeline-empty">No events yet. Trigger a control to start the session.</li>
        ) : (
          events.map((event, index) => (
            <li key={`${event.id ?? event.action}-${index}`} className="timeline-item">
              <div>
                <strong>{event.action}</strong>
                <span>{event.source}</span>
              </div>
              <time>{formatTimestamp(event.timestamp)}</time>
            </li>
          ))
        )}
      </ul>
    </section>
  );
}

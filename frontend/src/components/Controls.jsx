import React, { useState } from "react";
import { saveBoard, sendCommand, startFocus, stopFocus } from "../api";

export default function Controls() {
  const [status, setStatus] = useState("Ready");

  async function runAction(label, action) {
    try {
      await action();
      setStatus(`${label} sent`);
    } catch (error) {
      setStatus(`Error: ${error.message}`);
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Controls</h2>
        <p>{status}</p>
      </div>

      <div className="control-grid">
        <button onClick={() => runAction("Next slide", () => sendCommand("next_slide"))}>
          Next Slide
        </button>

        <button onClick={() => runAction("Previous slide", () => sendCommand("previous_slide"))}>
          Previous Slide
        </button>

        <button onClick={() => runAction("Start focus", startFocus)}>
          Start Focus
        </button>

        <button onClick={() => runAction("Stop focus", stopFocus)}>
          Stop Focus
        </button>

        <button className="accent" onClick={() => runAction("Save board", saveBoard)}>
          Save Board
        </button>
      </div>
    </section>
  );
}

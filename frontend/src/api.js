const BASE_URL = "http://localhost:8000";

async function postJson(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || "request_failed");
  }

  return data;
}

export async function sendCommand(action) {
  return postJson("/command", { action, source: "frontend" });
}

export async function startFocus() {
  return postJson("/focus/start", {});
}

export async function stopFocus() {
  return postJson("/focus/stop", {});
}

export async function saveBoard() {
  return postJson("/save-board", {});
}

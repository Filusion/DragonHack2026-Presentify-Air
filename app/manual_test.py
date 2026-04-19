from __future__ import annotations

import json
from urllib import error, request


BASE_URL = "http://127.0.0.1:8000"


def post(path: str, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req) as response:
            print(f"POST {path} -> {response.status}")
            print(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        print(f"POST {path} -> {exc.code}")
        print(exc.read().decode("utf-8"))


def get(path: str) -> None:
    req = request.Request(f"{BASE_URL}{path}", method="GET")
    with request.urlopen(req) as response:
        print(f"GET {path} -> {response.status}")
        print(response.read().decode("utf-8"))


if __name__ == "__main__":
    get("/health")
    post("/command", {"action": "next_slide", "source": "frontend"})
    post("/focus/start", {})
    post("/save-board", {})
    post("/vision/frame", {"gesture": "gesture_next_slide", "source": "vision"})
    get("/session/default")

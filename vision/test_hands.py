"""
test_hand.py — Live debug viewer

Controls:
  q  → quit
  p  → print raw landmarks to terminal
  d  → toggle debug overlay
  r  → reset gesture state
"""

import os
os.environ["GLOG_minloglevel"] = "3"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import cv2
import time
from hand_tracker import HandTracker, FINGER_NAMES
from gestures import GestureRecognizer

# ── Colour palette ────────────────────────────────────────────
C_YELLOW = (0,   255, 255)
C_GREEN  = (0,   255, 0  )
C_RED    = (0,   0,   255)
C_WHITE  = (255, 255, 255)
C_ORANGE = (0,   165, 255)
C_CYAN   = (255, 255, 0  )
C_PURPLE = (255, 0,   200)

# Colour per gesture for the banner
GESTURE_COLOURS = {
    "NEXT_SLIDE":       C_ORANGE,
    "PREV_SLIDE":       C_ORANGE,
    "OPEN_WHITEBOARD":  C_PURPLE,
    "CLOSE_WHITEBOARD": C_PURPLE,
    "WRITING":          C_GREEN,
}


def draw_hud(frame, hands, gesture, debug_info, show_debug, gesture_log):
    h, w = frame.shape[:2]

    # ── Gesture history log (top-right) ───────────────────
    for j, g in enumerate(reversed(gesture_log)):
        alpha = max(0.3, 1.0 - j * 0.18)
        col   = tuple(int(c * alpha) for c in GESTURE_COLOURS.get(g, C_WHITE))
        cv2.putText(frame, g, (w - 300, 50 + j * 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, col, 2)

    # ── Active gesture banner (bottom strip) ──────────────
    if gesture:
        col = GESTURE_COLOURS.get(gesture, C_WHITE)
        cv2.rectangle(frame, (0, h - 65), (w, h), (20, 20, 20), -1)
        cv2.putText(frame, f">> {gesture}", (20, h - 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.3, col, 3)

    if not show_debug or not hands:
        return

    # ── Debug dict (left side) ────────────────────────────
    y = 30
    for k, v in debug_info.items():
        # Highlight mp_gesture in yellow so it's easy to spot
        col = C_YELLOW if k == "mp_gesture" else C_WHITE
        cv2.putText(frame, f"{k}: {v}", (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.46, col, 1)
        y += 19

    # ── Pinch triangle: thumb / index / middle tips ───────
    hand = hands[0]
    tri  = [hand.landmarks_px[4][:2],   # thumb tip
            hand.landmarks_px[8][:2],   # index tip
            hand.landmarks_px[12][:2]]  # middle tip
    for a, b in [(0,1),(1,2),(2,0)]:
        cv2.line(frame, tri[a], tri[b], C_CYAN, 1)
    for pt in tri:
        cv2.circle(frame, pt, 7, C_RED, -1)


def print_landmarks(hands):
    if not hands:
        print("[No hands detected]")
        return
    for hand in hands:
        print(f"\n--- {hand.label} (score={hand.score:.2f}) mp_gesture={hand.mp_gesture} ---")
        for i, lm in enumerate(hand.landmarks):
            print(f"  [{i:2d}] {FINGER_NAMES[min(i//4,4)]:8s}"
                  f"  x={lm.x:.4f}  y={lm.y:.4f}  z={lm.z:.5f}")
        print(f"  fingers_up = {hand.fingers_up}")


def main():
    print("\n=== test_hand.py (MediaPipe Gesture Model) ===")
    print("Gestures:")
    print("  Open_Palm + swipe RIGHT  → NEXT_SLIDE")
    print("  Open_Palm + swipe LEFT   → PREV_SLIDE")
    print("  Victory ✌️  (hold)       → OPEN_WHITEBOARD")
    print("  Thumb_Up 👍 (hold)       → CLOSE_WHITEBOARD")
    print("  Pen pinch   (hold)       → WRITING")
    print("q=quit  p=landmarks  d=debug  r=reset\n")

    tracker    = HandTracker(max_hands=2, detection_confidence=0.5, tracking_confidence=0.4)
    recognizer = GestureRecognizer(
        swipe_threshold   = 0.18,  # ← tune if swipes are too easy/hard
        swipe_window      = 0.60,  # ← tune swipe speed requirement
        swipe_cooldown    = 1.00,
        wb_hold_frames    = 4,     # ← frames to hold Victory/Thumb_Up
        wb_cooldown       = 1.50,
        write_hold_frames = 3,     # ← frames to hold pen pinch
    )

    show_debug  = True
    print_next  = False
    gesture_log = []
    fps_time    = time.time()
    fps         = 0.0

    try:
        while True:
            frame = tracker.get_frame()
            hands = tracker.get_hands(frame)
            frame = tracker.draw(frame, hands)

            gesture    = recognizer.update(hands, frame.shape)
            debug_info = recognizer.get_debug_info(hands)

            # FPS counter (exponential moving average)
            now      = time.time()
            fps      = 0.9 * fps + 0.1 / max(now - fps_time, 1e-6)
            fps_time = now
            cv2.putText(frame, f"FPS:{fps:.0f}  Hands:{len(hands)}",
                        (frame.shape[1] - 185, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, C_WHITE, 1)

            # Log new gestures
            if gesture:
                if not gesture_log or gesture_log[-1] != gesture:
                    gesture_log.append(gesture)
                    gesture_log = gesture_log[-6:]
                    print(f"[GESTURE] {gesture}")

            draw_hud(frame, hands, gesture, debug_info, show_debug, gesture_log)
            cv2.imshow("test_hand — OAK-4S", frame)

            if print_next:
                print_landmarks(hands)
                print_next = False

            key = cv2.waitKey(1) & 0xFF
            if   key == ord('q'): break
            elif key == ord('p'): print_next = True
            elif key == ord('d'): show_debug = not show_debug
            elif key == ord('r'):
                recognizer = GestureRecognizer()
                gesture_log.clear()
                print("[reset]")

    finally:
        tracker.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
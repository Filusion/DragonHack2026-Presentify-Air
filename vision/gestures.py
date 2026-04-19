import time
from hand_tracker import (
    HandData,
    MP_GESTURE_OPEN_PALM, MP_GESTURE_VICTORY,
    MP_GESTURE_THUMB_UP,  MP_GESTURE_NONE,
)

GESTURE_NEXT_SLIDE       = "NEXT_SLIDE"
GESTURE_PREV_SLIDE       = "PREV_SLIDE"
GESTURE_OPEN_WHITEBOARD  = "OPEN_WHITEBOARD"
GESTURE_CLOSE_WHITEBOARD = "CLOSE_WHITEBOARD"
GESTURE_WRITING          = "WRITING"
GESTURE_NONE             = None


# ──────────────────────────────────────────────────────────────
#  Swipe tracker
# ──────────────────────────────────────────────────────────────
class SwipeTracker:
    def __init__(self, threshold=0.18, window_sec=0.60, cooldown_sec=1.00):
        self.threshold    = threshold
        self.window_sec   = window_sec
        self.cooldown_sec = cooldown_sec
        self._history: list[tuple[float, float]] = []
        self._last_swipe  = 0.0

    def update(self, norm_x: float) -> str | None:
        now = time.time()
        self._history.append((now, norm_x))
        self._history = [(t, v) for t, v in self._history if now - t <= self.window_sec]
        if len(self._history) < 2 or now - self._last_swipe < self.cooldown_sec:
            return None
        delta = self._history[-1][1] - self._history[0][1]
        if delta > self.threshold:
            self._last_swipe = now; self._history.clear(); return GESTURE_NEXT_SLIDE
        if delta < -self.threshold:
            self._last_swipe = now; self._history.clear(); return GESTURE_PREV_SLIDE
        return None

    def current_delta(self):
        if len(self._history) < 2: return 0.0
        return abs(self._history[-1][1] - self._history[0][1])

    def reset(self):
        self._history.clear()


# ──────────────────────────────────────────────────────────────
#  One-shot gesture detector
#  THE KEY FIX: fires ONCE per gesture occurrence, then requires
#  the gesture to be RELEASED before it can fire again.
#  This prevents a held Victory sign from repeatedly triggering
#  OPEN_WHITEBOARD and causing the page to flash/reload.
# ──────────────────────────────────────────────────────────────
class OneShotGestureDetector:
    """
    State machine:
      WAITING  → gesture seen for hold_frames → FIRED (returns True once)
      FIRED    → gesture still held            → silent (returns False)
      FIRED    → gesture released (seen=False) → WAITING (ready again)

    This guarantees exactly ONE event per physical gesture occurrence,
    regardless of how long the user holds it.
    """

    def __init__(self, hold_frames: int = 8):
        # Raise hold_frames if gestures fire too easily (e.g. from arm posture)
        # Lower if gestures feel unresponsive. Range: 5–15
        self.hold_frames = hold_frames
        self._count  = 0      # consecutive frames gesture has been seen
        self._fired  = False  # True after firing, until gesture is released

    def update(self, seen: bool) -> bool:
        if seen:
            if self._fired:
                return False   # already fired this occurrence — stay silent
            self._count += 1
            if self._count >= self.hold_frames:
                self._fired = True
                return True    # fire exactly once
            return False
        else:
            # Gesture not present — reset so next occurrence can fire
            self._count = 0
            self._fired = False
            return False

    def reset(self):
        self._count = 0
        self._fired = False


# ──────────────────────────────────────────────────────────────
#  Writing grip
# ──────────────────────────────────────────────────────────────
def _dist(a, b):
    return ((a[0]-b[0])**2 + (a[1]-b[1])**2) ** 0.5

def is_writing_grip(hand: HandData) -> bool:
    PINCH_RATIO = 0.35
    thumb_tip  = hand.landmarks_px[4]
    index_tip  = hand.landmarks_px[8]
    middle_tip = hand.landmarks_px[12]
    wrist      = hand.landmarks_px[0]
    mid_mcp    = hand.landmarks_px[9]
    hand_size  = _dist(wrist, mid_mcp) or 1.0
    d_ti = _dist(thumb_tip, index_tip)  / hand_size
    d_tm = _dist(thumb_tip, middle_tip) / hand_size
    d_im = _dist(index_tip, middle_tip) / hand_size
    return d_ti < PINCH_RATIO and d_tm < PINCH_RATIO and d_im < PINCH_RATIO


# ──────────────────────────────────────────────────────────────
#  Main gesture recognizer
# ──────────────────────────────────────────────────────────────
class GestureRecognizer:
    """
    RIGHT HAND ONLY — ignores any hand MediaPipe labels as "Left".

    Gesture → Action:
      Open_Palm + swipe right → NEXT_SLIDE
      Open_Palm + swipe left  → PREV_SLIDE
      Victory ✌️  (hold 8fr)  → OPEN_WHITEBOARD  (fires once, requires release)
      Thumb_Up 👍 (hold 8fr)  → CLOSE_WHITEBOARD (fires once, requires release)
      Pen pinch   (hold 3fr)  → WRITING (continuous while held)
    """

    def __init__(
        self,
        swipe_threshold:   float = 0.18,
        swipe_window:      float = 0.60,
        swipe_cooldown:    float = 1.00,
        wb_hold_frames:    int   = 8,    # frames to hold Victory/Thumb_Up before firing
        write_hold_frames: int   = 3,
    ):
        self.swipe = SwipeTracker(swipe_threshold, swipe_window, swipe_cooldown)

        # One-shot detectors — each fires ONCE per occurrence
        self._victory_det = OneShotGestureDetector(wb_hold_frames)
        self._thumbup_det = OneShotGestureDetector(wb_hold_frames)

        self.write_hold_frames = write_hold_frames
        self._write_count  = 0
        self._write_active = False

    def _get_right_hand(self, hands: list[HandData]) -> HandData | None:
        """
        Return the first Right hand from the list, or None.
        MediaPipe reports handedness from the model's perspective
        (mirrored camera), so "Right" = the user's right hand.
        """
        for hand in hands:
            if hand.label == "Right":
                return hand
        return None

    def update(self, hands: list[HandData], frame_shape: tuple) -> str | None:
        # Filter to right hand only
        hand = self._get_right_hand(hands)

        if hand is None:
            # No right hand — reset all state
            self.swipe.reset()
            self._victory_det.reset()
            self._thumbup_det.reset()
            self._write_count  = 0
            self._write_active = False
            return None

        mp_g = hand.mp_gesture

        # 1. Slide change: Open_Palm + horizontal swipe
        if mp_g == MP_GESTURE_OPEN_PALM:
            norm_x = hand.landmarks[0].x
            result = self.swipe.update(norm_x)
            if result:
                return result
        else:
            self.swipe.reset()

        # 2. Open whiteboard: Victory ✌️ (one-shot)
        if self._victory_det.update(mp_g == MP_GESTURE_VICTORY):
            return GESTURE_OPEN_WHITEBOARD

        # 3. Close whiteboard: Thumb_Up 👍 (one-shot)
        if self._thumbup_det.update(mp_g == MP_GESTURE_THUMB_UP):
            return GESTURE_CLOSE_WHITEBOARD

        # 4. Writing: pen pinch (continuous while held)
        writing = is_writing_grip(hand)
        if writing:
            self._write_count += 1
            if self._write_count >= self.write_hold_frames:
                self._write_active = True
            if self._write_active:
                return GESTURE_WRITING
        else:
            self._write_count  = 0
            self._write_active = False

        return None

    def get_debug_info(self, hands: list[HandData]) -> dict:
        hand = self._get_right_hand(hands)
        if not hand:
            return {"hands": len(hands), "right_hand": False}
        thumb_tip  = hand.landmarks_px[4]
        index_tip  = hand.landmarks_px[8]
        middle_tip = hand.landmarks_px[12]
        wrist      = hand.landmarks_px[0]
        mid_mcp    = hand.landmarks_px[9]
        hand_size  = _dist(wrist, mid_mcp) or 1.0
        return {
            "hands":        len(hands),
            "right_hand":   True,
            "mp_gesture":   hand.mp_gesture,
            "open_palm":    hand.is_open_palm(),
            "swipe_delta":  round(self.swipe.current_delta(), 3),
            "wrist_x":      round(hand.landmarks[0].x, 3),
            "pinch_TI":     round(_dist(thumb_tip, index_tip)  / hand_size, 2),
            "pinch_TM":     round(_dist(thumb_tip, middle_tip) / hand_size, 2),
            "pinch_IM":     round(_dist(index_tip, middle_tip) / hand_size, 2),
            "writing_grip": is_writing_grip(hand),
            "write_hold":   f"{self._write_count}/{self.write_hold_frames}",
            "v_count":      f"{self._victory_det._count}/{self._victory_det.hold_frames}",
            "t_count":      f"{self._thumbup_det._count}/{self._thumbup_det.hold_frames}",
        }

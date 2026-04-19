import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from camera import Camera
import urllib.request
import os

# ─────────────────────────────────────────────
#  Auto-download models
# ─────────────────────────────────────────────
LANDMARK_MODEL_PATH = "hand_landmarker.task"
GESTURE_MODEL_PATH  = "gesture_recognizer.task"

LANDMARK_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
GESTURE_MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/latest/gesture_recognizer.task"

for path, url in [(LANDMARK_MODEL_PATH, LANDMARK_MODEL_URL),
                  (GESTURE_MODEL_PATH,  GESTURE_MODEL_URL)]:
    if not os.path.exists(path):
        print(f"Downloading {path}...")
        urllib.request.urlretrieve(url, path)
        print("Done.")

# ─────────────────────────────────────────────
#  Landmark index constants
# ─────────────────────────────────────────────
WRIST       = 0
THUMB_TIP   = 4;  THUMB_IP  = 3
INDEX_TIP   = 8;  INDEX_PIP = 6
MIDDLE_TIP  = 12; MIDDLE_PIP= 10
RING_TIP    = 16; RING_PIP  = 14
PINKY_TIP   = 20; PINKY_PIP = 18

FINGER_TIPS  = [THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
FINGER_PIPS  = [THUMB_IP,  INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP]
FINGER_NAMES = ["Thumb", "Index", "Middle", "Ring", "Pinky"]

HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17),
]

# MediaPipe Gesture Recognizer returns these gesture name strings.
# Full list of built-in gestures:
#   "None", "Closed_Fist", "Open_Palm", "Pointing_Up",
#   "Thumb_Down", "Thumb_Up", "Victory", "ILoveYou"
MP_GESTURE_OPEN_PALM   = "Open_Palm"
MP_GESTURE_CLOSED_FIST = "Closed_Fist"
MP_GESTURE_VICTORY     = "Victory"
MP_GESTURE_THUMB_UP    = "Thumb_Up"
MP_GESTURE_THUMB_DOWN  = "Thumb_Down"
MP_GESTURE_POINTING_UP = "Pointing_Up"
MP_GESTURE_NONE        = "None"


class HandData:
    """
    All processed data for one detected hand, combining:
      - 21 landmark positions (raw + pixel)
      - finger-up booleans
      - MediaPipe classified gesture string (e.g. "Open_Palm", "Victory")
    """
    def __init__(self, landmarks, landmarks_px, label, score, fingers_up, mp_gesture):
        self.landmarks    = landmarks       # raw NormalizedLandmark list
        self.landmarks_px = landmarks_px   # list of (x_px, y_px, z)
        self.label        = label           # "Left" or "Right"
        self.score        = score           # handedness confidence
        self.fingers_up   = fingers_up     # [thumb, index, middle, ring, pinky]
        self.mp_gesture   = mp_gesture     # string from MediaPipe gesture model
        self.wrist_px     = landmarks_px[WRIST]
        self.index_tip_px = landmarks_px[INDEX_TIP]
        self.thumb_tip_px = landmarks_px[THUMB_TIP]

    def is_open_palm(self) -> bool:
        """True if MediaPipe classifies the gesture as Open_Palm."""
        return self.mp_gesture == MP_GESTURE_OPEN_PALM

    def is_victory(self) -> bool:
        """True if MediaPipe classifies the gesture as Victory (✌️)."""
        return self.mp_gesture == MP_GESTURE_VICTORY

    def is_thumb_up(self) -> bool:
        """True if MediaPipe classifies the gesture as Thumb_Up (👍)."""
        return self.mp_gesture == MP_GESTURE_THUMB_UP


class HandTracker:
    """
    Wraps MediaPipe Tasks GestureRecognizer (v0.10+).

    We use GestureRecognizer instead of HandLandmarker because it:
      1. Returns the same 21 landmarks
      2. ALSO returns a classified gesture string (Open_Palm, Victory, etc.)
         which is much more reliable than our manual finger-state logic.

    Running mode VIDEO applies temporal smoothing → stable tracking.

    ┌──────────────────────────────────────────────────────────┐
    │  TUNING                                                  │
    │  detection_confidence  default 0.5                       │
    │    Lower → detects hand in more difficult conditions     │
    │    raise → fewer false positives                         │
    │                                                          │
    │  tracking_confidence   default 0.4                       │
    │    Lower → holds tracking longer before dropping hand    │
    └──────────────────────────────────────────────────────────┘
    """

    def __init__(
        self,
        camera: Camera = None,
        max_hands: int             = 1,
        detection_confidence: float = 0.5,
        tracking_confidence:  float = 0.4,
        model_path: str            = GESTURE_MODEL_PATH,
    ):
        self.camera = camera or Camera()

        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.GestureRecognizerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,   # temporal smoothing
            num_hands=max_hands,
            min_hand_detection_confidence=detection_confidence,
            min_hand_presence_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )
        self.recognizer  = mp_vision.GestureRecognizer.create_from_options(options)
        self._frame_ts   = 0   # strictly increasing ms timestamp for VIDEO mode

    # ──────────────────────────────────────────
    #  Main method — call every frame
    # ──────────────────────────────────────────

    def get_hands(self, frame: np.ndarray) -> list[HandData]:
        """
        Process one BGR frame. Returns list[HandData], one per detected hand.
        Empty list if no hands found.
        """
        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # VIDEO mode needs a strictly increasing timestamp in milliseconds
        self._frame_ts += 33
        result = self.recognizer.recognize_for_video(mp_image, self._frame_ts)

        hands = []
        h, w  = frame.shape[:2]

        for i, lms in enumerate(result.hand_landmarks):
            # Handedness — "Left" or "Right"
            label = result.handedness[i][0].display_name if result.handedness else "Right"
            score = result.handedness[i][0].score        if result.handedness else 0.0

            # Convert normalized landmarks to pixel coordinates
            lms_px = [(int(lm.x * w), int(lm.y * h), lm.z) for lm in lms]

            # Per-finger extended/curled booleans
            fingers = self._fingers_up(lms_px, label)

            # MediaPipe classified gesture string for this hand
            # result.gestures[i] is a list of classifications, take the top one
            mp_gesture = MP_GESTURE_NONE
            if result.gestures and i < len(result.gestures) and result.gestures[i]:
                mp_gesture = result.gestures[i][0].category_name

            hands.append(HandData(lms, lms_px, label, score, fingers, mp_gesture))

        return hands

    # ──────────────────────────────────────────
    #  Drawing
    # ──────────────────────────────────────────

    def draw(self, frame: np.ndarray, hands: list[HandData]) -> np.ndarray:
        """Draw skeleton, landmarks, gesture label and wrist label onto a copy of frame."""
        out = frame.copy()
        for hand in hands:
            pts = [(x, y) for x, y, _ in hand.landmarks_px]

            # Skeleton connections
            for a, b in HAND_CONNECTIONS:
                cv2.line(out, pts[a], pts[b], (255, 255, 255), 2)

            # Landmark dots — fingertips are larger and red
            for j, pt in enumerate(pts):
                is_tip = j in FINGER_TIPS
                cv2.circle(out, pt, 6 if is_tip else 4,
                           (0, 0, 255) if is_tip else (0, 255, 0), -1)

            # Wrist label: handedness + MediaPipe gesture
            wx, wy, _ = hand.wrist_px
            cv2.putText(out, f"{hand.label} | {hand.mp_gesture}",
                        (wx - 40, wy - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)

        return out

    # ──────────────────────────────────────────
    #  Internal helpers
    # ──────────────────────────────────────────

    def _fingers_up(self, lms_px: list, label: str) -> list[bool]:
        """
        Returns [thumb, index, middle, ring, pinky] — True = extended.
        Thumb uses X-axis comparison (mirrored for left hand).
        Other fingers use Y-axis: tip.y < pip.y means the tip is higher = extended.
        """
        up = []
        # Thumb: horizontal check, mirrored for left hand
        up.append(lms_px[THUMB_TIP][0] < lms_px[THUMB_IP][0]
                  if label == "Right"
                  else lms_px[THUMB_TIP][0] > lms_px[THUMB_IP][0])
        # Index → Pinky: vertical check
        for tip, pip in zip(FINGER_TIPS[1:], FINGER_PIPS[1:]):
            up.append(lms_px[tip][1] < lms_px[pip][1])
        return up

    # ──────────────────────────────────────────
    #  Convenience pass-throughs
    # ──────────────────────────────────────────

    def get_frame(self) -> np.ndarray:
        return self.camera.get_frame()

    def release(self):
        self.recognizer.close()
        self.camera.release()

    def __enter__(self):    return self
    def __exit__(self, *_): self.release()
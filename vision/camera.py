import cv2

class Camera:
    def __init__(self, cam_id=0, resolution=(1920, 1080)):
        self.cam_id = cam_id
        self.resolution = resolution
        self.cap = cv2.VideoCapture(self.cam_id)

        # optional: set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

        if not self.cap.isOpened():
            raise RuntimeError("Cannot open webcam")

    def get_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("Failed to read frame")
        return frame

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()
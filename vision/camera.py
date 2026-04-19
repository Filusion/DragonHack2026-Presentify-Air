import depthai as dai
import cv2

class Camera:
    def __init__(self, resolution=(1920, 1080), socket=dai.CameraBoardSocket.CAM_A):
        self.resolution = resolution
        self.socket = socket
        self._pipeline = None
        self._queue = None
        self._start()

    def _start(self):
        self._pipeline = dai.Pipeline()
        self._pipeline.__enter__()
        cam = self._pipeline.create(dai.node.Camera).build(self.socket)
        self._queue = cam.requestOutput(self.resolution, dai.ImgFrame.Type.BGR888i).createOutputQueue()
        self._pipeline.start()

    def get_frame(self):
        frame: dai.ImgFrame = self._queue.get()
        return frame.getCvFrame()

    def release(self):
        if self._pipeline:
            self._pipeline.__exit__(None, None, None)
            self._pipeline = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()
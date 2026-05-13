from __future__ import annotations

import threading
import time

import cv2

from reconnaissance import FaceRecognizer, log_recognition


class CameraStream:
    def __init__(self, on_frame=None, on_event=None, confidence_threshold: float = 55.0):
        self.on_frame = on_frame
        self.on_event = on_event
        self.recognizer = FaceRecognizer(confidence_threshold=confidence_threshold)
        self.running = False
        self.capture = None
        self.thread = None
        self.last_granted = 0.0
        self.paused = False
        self.process_scale = 0.65
        self._last_frame_emit = 0.0
        self._last_process = 0.0
        self._last_detections = []

    def start(self, index: int = 0):
        if self.running:
            return
        self.capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not self.capture.isOpened():
            self.capture = cv2.VideoCapture(index)
        if not self.capture.isOpened():
            raise RuntimeError("Unable to open camera.")
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def toggle_pause(self):
        self.paused = not self.paused
        return self.paused

    def _loop(self):
        while self.running and self.capture is not None:
            ok, frame = self.capture.read()
            if not ok:
                time.sleep(0.03)
                continue
            if self.paused:
                if self.on_frame:
                    self.on_frame(frame)
                time.sleep(0.05)
                continue
            frame = cv2.flip(frame, 1)
            annotated = frame
            detections = []
            now = time.time()
            if now - self._last_process >= 0.08:
                annotated, detections = self.recognizer.detect_and_annotate(frame, scale=self.process_scale)
                self._last_process = now
                self._last_detections = detections
            else:
                detections = self._last_detections
            now = time.time()
            for det in detections:
                if det["status"] == "AUTHORIZED" and det["confidence"] is not None:
                    if now - self.last_granted >= 10:
                        self.last_granted = now
                        log_recognition(det["label"], "AUTHORIZED", det["confidence"])
                        if self.on_event:
                            self.on_event(det)
                elif det["label"] == "Unknown":
                    log_recognition("Unknown", "REFUSED", det["confidence"])
            if self.on_frame:
                self.on_frame(annotated)
            time.sleep(0.01)

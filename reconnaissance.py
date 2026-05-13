from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from config import DATASET_DIR, MODEL_PATH, USERS_PATH, CASCADE_PATH
from historique import add_log
from tatouage import attach_watermark


def ensure_storage():
    DATASET_DIR.mkdir(exist_ok=True)
    if not USERS_PATH.exists():
        USERS_PATH.write_text("[]", encoding="utf-8")


def load_users():
    ensure_storage()
    try:
        return json.loads(USERS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_users(users):
    USERS_PATH.write_text(json.dumps(users, indent=2, ensure_ascii=False), encoding="utf-8")


def next_user_id(users):
    ids = [int(u.get("id", 0)) for u in users if str(u.get("id", "")).isdigit()]
    return str(max(ids, default=0) + 1)


def get_user_by_id(user_id: str):
    for user in load_users():
        if str(user.get("id")) == str(user_id):
            return user
    return None


def _face_recognizer():
    if not hasattr(cv2, "face"):
        raise RuntimeError("OpenCV contrib module is required for LBPH face recognition.")
    return cv2.face.LBPHFaceRecognizer_create()


def train_model():
    ensure_storage()
    images = []
    labels = []
    users = load_users()
    for user in users:
        user_id = str(user.get("id"))
        user_dir = DATASET_DIR / f"user_{user_id}"
        if not user_dir.exists():
            continue
        for file in user_dir.glob("*.png"):
            img = cv2.imread(str(file), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            images.append(img)
            labels.append(int(user_id))
    if not images:
        raise RuntimeError("No face images found for training.")
    recognizer = _face_recognizer()
    recognizer.train(images, np.array(labels))
    recognizer.save(str(MODEL_PATH))
    return True


def delete_user_everywhere(user_id: str):
    users = [u for u in load_users() if str(u.get("id")) != str(user_id)]
    save_users(users)
    user_dir = DATASET_DIR / f"user_{user_id}"
    if user_dir.exists():
        for file in user_dir.glob("*"):
            file.unlink(missing_ok=True)
        user_dir.rmdir()


class FaceRecognizer:
    def __init__(self, confidence_threshold: float = 55.0):
        self.confidence_threshold = confidence_threshold
        self.cascade = cv2.CascadeClassifier(str(CASCADE_PATH))
        self.recognizer = None
        if MODEL_PATH.exists() and hasattr(cv2, "face"):
            try:
                self.recognizer = _face_recognizer()
                self.recognizer.read(str(MODEL_PATH))
            except Exception:
                self.recognizer = None

    def detect_and_annotate(self, frame, scale: float = 1.0):
        original = frame
        working = frame
        if scale != 1.0:
            working = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        gray = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY)
        faces = []
        if not self.cascade.empty():
            faces = self.cascade.detectMultiScale(gray, 1.3, 5)
        results = []
        for (x, y, w, h) in faces:
            roi = gray[y : y + h, x : x + w]
            label = "Unknown"
            confidence = None
            status = "REFUSED"
            color = (0, 84, 255)
            if self.recognizer is not None and roi.size > 0:
                roi = cv2.resize(roi, (200, 200))
                pred_id, conf = self.recognizer.predict(roi)
                confidence = round(float(conf), 1)
                user = get_user_by_id(str(pred_id))
                if user and conf <= self.confidence_threshold:
                    label = user.get("name", f"User {pred_id}")
                    status = "AUTHORIZED"
                    color = (0, 220, 140)
                else:
                    label = "Unknown"
            if scale != 1.0:
                x, y, w, h = [int(v / scale) for v in (x, y, w, h)]
            cv2.rectangle(original, (x, y), (x + w, y + h), color, 2, cv2.LINE_AA)
            overlay_y = max(30, y - 10)
            cv2.rectangle(original, (x, overlay_y - 28), (x + w, overlay_y), color, -1, cv2.LINE_AA)
            cv2.putText(original, label, (x + 8, overlay_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
            if confidence is not None:
                cv2.putText(original, f"{confidence:.1f}", (x + 8, y + h + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
            results.append({
                "bbox": (x, y, w, h),
                "label": label,
                "confidence": confidence,
                "status": status,
            })
        return original, results


def log_recognition(user_name: str, status: str, confidence: float | None, user_id: str | None = None):
    payload = attach_watermark(
        {
            "user_name": user_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        }
    )
    add_log(user_name=user_name, status=status, confidence=confidence, user_id=user_id, watermark=payload["watermark"])

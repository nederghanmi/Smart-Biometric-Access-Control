from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import cv2


BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset"
MODEL_PATH = BASE_DIR / "modele.yml"
LOG_DB_PATH = BASE_DIR / "logs.db"
USERS_PATH = BASE_DIR / "utilisateurs.json"
CONSENT_PATH = BASE_DIR / "rgpd_consent.json"
CASCADE_PATH = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
APP_TITLE = "Smart Biometric Access Control"


@dataclass(frozen=True)
class UiTheme:
    bg: str = "#07111f"
    panel: str = "#0d1b2a"
    panel_alt: str = "#10263d"
    accent: str = "#2f80ff"
    accent_2: str = "#00d4ff"
    success: str = "#1dd1a1"
    warning: str = "#ffb400"
    danger: str = "#ff5c77"
    text: str = "#e6f0ff"
    muted: str = "#8aa4c2"


THEME = UiTheme()

# Smart Biometric Access Control

Smart Biometric Access Control is a Python desktop application for local biometric access management. It uses face recognition to identify users, records access events in SQLite, and keeps user data on the machine.

## Features

- Real-time face detection and recognition with OpenCV
- LBPH-based model training and prediction
- Local SQLite access logs
- User registration and deletion
- Dataset capture for each user
- RGPD-style consent workflow
- Modern Tkinter interface with `ttkbootstrap` support

## Requirements

- Python 3.10 or newer
- OpenCV with contrib modules
- NumPy
- Pillow
- ttkbootstrap

## Installation

```bash
git clone https://github.com/nederghanmi/Smart-Biometric-Access-Control.git
cd Smart-Biometric-Access-Control
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Project Structure

```text
main.py                  Application entry point
interface.py             Main desktop UI
reconnaissance.py        Face recognition and model training
camera.py                Camera capture loop
historique.py            Log storage and reporting
tatouage.py              Watermark utilities
alertes.py               Toast notifications
config.py                Paths, titles, and theme values
requirements.txt         Python dependencies
```

## Data Files

The application creates and uses local runtime data automatically:

- `dataset/` for captured face images
- `logs.db` for access logs
- `modele.yml` for the trained recognition model
- `utilisateurs.json` for registered users
- `rgpd_consent.json` for consent state

These files are ignored in Git because they are generated locally and may contain machine-specific data.

## Notes

- `opencv-contrib-python` is required because the project uses LBPH face recognition.
- The first launch may create local files and folders automatically.
- This project is designed for local use and demo environments.

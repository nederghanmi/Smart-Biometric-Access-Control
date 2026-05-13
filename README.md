# Smart Biometric Access Control

> Offline Python desktop app for face recognition, biometric access control, and local audit logging.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8)
![Tkinter](https://img.shields.io/badge/Tkinter-Desktop%20UI-1C7ED6)
![SQLite](https://img.shields.io/badge/SQLite-Local%20Storage-003B57)

Smart Biometric Access Control is a local Python desktop application for biometric identity verification and access monitoring. It combines face recognition, structured user management, and SQLite-based audit logging in a single offline-first system designed for demos, labs, and controlled environments.

## Overview

The application captures and processes face images locally, trains an LBPH recognition model, and records access attempts with timestamps and confidence scores. User data, datasets, and logs remain on the machine instead of being sent to external services.

## Highlights

- Offline-first design with local storage only
- Face recognition powered by OpenCV and LBPH
- Access history stored in SQLite
- User enrollment and deletion workflow
- Modern dark-themed desktop interface
- RGPD-style consent prompt for local compliance flow

## Features

- Real-time face detection and recognition with OpenCV
- LBPH-based model training and prediction
- Local SQLite access logs
- User registration and deletion
- Dataset capture for each user
- RGPD-style consent workflow
- Modern Tkinter interface with `ttkbootstrap` support
- Offline-first local storage
- Simple admin workflow for managing users and logs

## Use Cases

- Laboratory biometric access demos
- Academic computer vision projects
- Local attendance or entry logging prototypes
- Controlled access monitoring on a single machine

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

## Screenshots

Add screenshots here once you capture the interface:

- Main dashboard
- Admin panel
- Access log view

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

## GitHub Keywords

Suggested repository topics:

`python`, `opencv`, `face-recognition`, `biometric`, `access-control`, `desktop-app`, `tkinter`, `sqlite`, `computer-vision`, `security`

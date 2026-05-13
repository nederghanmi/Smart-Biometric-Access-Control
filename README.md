# Smart Biometric Access Control

Smart Biometric Access Control is a Python desktop app for biometric access control with:

- LBPH face recognition
- dataset capture
- secure SQLite logging
- RGPD-style user deletion
- modern dark cybersecurity interface

## Run

```bash
pip install -r requirements.txt
python main.py
```

## Notes

- `opencv-contrib-python` is required for LBPH.
- The first launch will create local storage files and folders automatically.

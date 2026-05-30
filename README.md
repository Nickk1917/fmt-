# File Converter Web App

A simple Flask-based converter with a frontend page for uploading files and downloading converted output.

## Requirements

- Python 3.10+
- `ffmpeg` installed and available on your system `PATH`

## Install dependencies

From the project folder:

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Install ffmpeg on Windows

### Option 1: winget (recommended)

```powershell
winget install ffmpeg
```

### Option 2: Chocolatey

```powershell
choco install ffmpeg
```

### Option 3: Manual install

1. Download a Windows build from https://ffmpeg.org/download.html
2. Extract the archive
3. Add the folder containing `ffmpeg.exe` to your system `PATH`

## Run the app

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:5000/
```

## Supported conversions

- Video inputs: `mp4`, `mov`, `avi`, `wmv`, `mkv`
- Audio inputs: `mp3`, `wav`, `flac`, `ogg`
- Image inputs: `jpg`, `jpeg`, `png`, `webp`, `gif`, `bmp`
- Document input: `pdf`

- Output formats:
  - Video → `mp4`, `mp3`, `wav`, `mov`, `webm`
  - Audio → `mp3`, `wav`
  - Image → `jpg`, `png`, `webp`
  - PDF → `docx`

## Notes

- Audio/video conversions require `ffmpeg`.
- If conversion fails with an `ffmpeg` error, make sure `ffmpeg` is installed and in `PATH`.

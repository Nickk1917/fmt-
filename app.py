import os
import uuid
import shutil
import subprocess
from flask import Flask, request, jsonify, send_file, after_this_request
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── Supported format groups ───────────────────────────────────────────────────
VIDEO_EXTS  = {"mp4", "mov", "avi", "wmv", "mkv", "webm"}
AUDIO_EXTS  = {"mp3", "wav", "flac", "ogg", "aac", "m4a"}
IMAGE_EXTS  = {"jpg", "jpeg", "png", "webp", "gif", "bmp", "tiff"}

# What each input type can be converted TO
ALLOWED_CONVERSIONS = {
    # video → video or audio
    "mp4":  VIDEO_EXTS | AUDIO_EXTS,
    "mov":  VIDEO_EXTS | AUDIO_EXTS,
    "avi":  VIDEO_EXTS | AUDIO_EXTS,
    "wmv":  VIDEO_EXTS | AUDIO_EXTS,
    "mkv":  VIDEO_EXTS | AUDIO_EXTS,
    "webm": VIDEO_EXTS | AUDIO_EXTS,
    # audio → audio only
    "mp3":  AUDIO_EXTS,
    "wav":  AUDIO_EXTS,
    "flac": AUDIO_EXTS,
    "ogg":  AUDIO_EXTS,
    "aac":  AUDIO_EXTS,
    "m4a":  AUDIO_EXTS,
    # image → image
    "jpg":  IMAGE_EXTS,
    "jpeg": IMAGE_EXTS,
    "png":  IMAGE_EXTS,
    "webp": IMAGE_EXTS,
    "gif":  IMAGE_EXTS,
    "bmp":  IMAGE_EXTS,
    "tiff": IMAGE_EXTS,
    # document
    "pdf":  {"docx"},
}

# PIL save format names (PIL is picky about these)
PIL_FORMAT_MAP = {
    "jpg":  "JPEG",
    "jpeg": "JPEG",
    "png":  "PNG",
    "webp": "WEBP",
    "gif":  "GIF",
    "bmp":  "BMP",
    "tiff": "TIFF",
}


# ── FFmpeg finder ─────────────────────────────────────────────────────────────
def get_ffmpeg():
    """Return path to ffmpeg binary, or raise a clear error."""
    # 1. Check PATH first
    ffmpeg = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if ffmpeg:
        return ffmpeg
    # 2. Fall back to imageio_ffmpeg bundled binary
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        return get_ffmpeg_exe()
    except Exception:
        pass
    raise EnvironmentError(
        "ffmpeg not found. Run: pip install imageio-ffmpeg   OR install ffmpeg and add it to PATH."
    )


def run_ffmpeg(args, timeout=600):
    """
    Run ffmpeg with the given argument list.
    Raises RuntimeError with ffmpeg's stderr output on failure.
    """
    ffmpeg = get_ffmpeg()
    cmd = [ffmpeg, "-y"] + args   # -y = overwrite output without asking
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="replace").strip()
        # Give the user the last 3 lines (most relevant)
        short = "\n".join(err.splitlines()[-3:])
        raise RuntimeError(f"FFmpeg error:\n{short}")
    return result


# ── Core conversion logic ─────────────────────────────────────────────────────
def convert_file(input_path, output_format):
    ext = output_format.lower()
    input_ext = input_path.rsplit(".", 1)[-1].lower()

    # Validate the conversion is allowed
    allowed = ALLOWED_CONVERSIONS.get(input_ext, set())
    if ext not in allowed:
        raise ValueError(
            f"Cannot convert .{input_ext} → .{ext}. "
            f"Allowed targets: {', '.join(sorted(allowed)) or 'none'}"
        )

    output_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_out.{ext}")

    # ── Image conversions (Pillow) ────────────────────────────────────────────
    if input_ext in IMAGE_EXTS and ext in IMAGE_EXTS:
        from PIL import Image
        with Image.open(input_path) as img:
            pil_fmt = PIL_FORMAT_MAP[ext]
            # JPEG doesn't support transparency — convert to RGB
            if pil_fmt == "JPEG" and img.mode in ("RGBA", "P", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background
            elif pil_fmt != "GIF":
                img = img.convert("RGB") if pil_fmt == "JPEG" else img
            img.save(output_path, format=pil_fmt)

    # ── PDF → DOCX ───────────────────────────────────────────────────────────
    elif input_ext == "pdf" and ext == "docx":
        from pdf2docx import Converter
        cv = Converter(input_path)
        cv.convert(output_path, start=0, end=None)
        cv.close()

    # ── Video → Audio (FFmpeg, very fast) ────────────────────────────────────
    elif input_ext in VIDEO_EXTS and ext in AUDIO_EXTS:
        # Just extract the audio stream — no re-encoding of video needed
        if ext == "mp3":
            run_ffmpeg(["-i", input_path, "-vn", "-acodec", "libmp3lame", "-q:a", "2", output_path])
        elif ext == "wav":
            run_ffmpeg(["-i", input_path, "-vn", "-acodec", "pcm_s16le", output_path])
        elif ext == "flac":
            run_ffmpeg(["-i", input_path, "-vn", "-acodec", "flac", output_path])
        elif ext == "ogg":
            run_ffmpeg(["-i", input_path, "-vn", "-acodec", "libvorbis", output_path])
        elif ext == "aac":
            run_ffmpeg(["-i", input_path, "-vn", "-acodec", "aac", output_path])
        elif ext == "m4a":
            run_ffmpeg(["-i", input_path, "-vn", "-acodec", "aac", output_path])
        else:
            run_ffmpeg(["-i", input_path, "-vn", output_path])

    # ── Audio → Audio (FFmpeg) ────────────────────────────────────────────────
    elif input_ext in AUDIO_EXTS and ext in AUDIO_EXTS:
        if ext == "mp3":
            run_ffmpeg(["-i", input_path, "-acodec", "libmp3lame", "-q:a", "2", output_path])
        elif ext == "wav":
            run_ffmpeg(["-i", input_path, "-acodec", "pcm_s16le", output_path])
        elif ext == "flac":
            run_ffmpeg(["-i", input_path, "-acodec", "flac", output_path])
        elif ext == "ogg":
            run_ffmpeg(["-i", input_path, "-acodec", "libvorbis", output_path])
        elif ext == "aac":
            run_ffmpeg(["-i", input_path, "-acodec", "aac", output_path])
        else:
            run_ffmpeg(["-i", input_path, output_path])

    # ── Video → Video (FFmpeg) ────────────────────────────────────────────────
    elif input_ext in VIDEO_EXTS and ext in VIDEO_EXTS:
        if ext == "mp4":
            # libx264 is the most compatible MP4 codec
            run_ffmpeg([
                "-i", input_path,
                "-vcodec", "libx264",
                "-acodec", "aac",
                "-preset", "fast",      # fast = good speed/quality tradeoff
                "-crf", "23",           # quality (18=great, 28=smaller file)
                output_path,
            ])
        elif ext == "webm":
            run_ffmpeg([
                "-i", input_path,
                "-vcodec", "libvpx-vp9",
                "-acodec", "libvorbis",
                "-crf", "33",
                "-b:v", "0",
                output_path,
            ])
        elif ext in {"mov", "avi", "mkv"}:
            # Copy streams when possible (fastest — no re-encoding)
            run_ffmpeg([
                "-i", input_path,
                "-vcodec", "copy",
                "-acodec", "copy",
                output_path,
            ])
        else:
            run_ffmpeg(["-i", input_path, output_path])

    else:
        raise ValueError(f"Unsupported conversion: .{input_ext} → .{ext}")

    # Sanity check — make sure we actually produced a file
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("Conversion produced an empty file. Check ffmpeg logs.")

    return output_path


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_file("index.html")


@app.route("/api/formats", methods=["GET"])
def get_formats():
    return jsonify({
        "video":    {"from": list(VIDEO_EXTS),  "to": list(VIDEO_EXTS | AUDIO_EXTS)},
        "audio":    {"from": list(AUDIO_EXTS),  "to": list(AUDIO_EXTS)},
        "image":    {"from": list(IMAGE_EXTS),  "to": list(IMAGE_EXTS)},
        "document": {"from": ["pdf"],            "to": ["docx"]},
    })


@app.route("/api/convert", methods=["POST"])
def convert():
    if "file" not in request.files:
        return jsonify({"error": "No file sent"}), 400

    file = request.files["file"]
    target_format = request.form.get("format", "").strip().lower().lstrip(".")

    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400
    if not target_format:
        return jsonify({"error": "No target format specified"}), 400

    filename   = secure_filename(file.filename)
    input_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{filename}")
    file.save(input_path)

    output_path = None
    try:
        output_path = convert_file(input_path, target_format)

        @after_this_request
        def cleanup(response):
            try:
                if output_path and os.path.exists(output_path):
                    os.remove(output_path)
            except Exception:
                pass
            return response

        return send_file(output_path, as_attachment=True)

    except (ValueError, EnvironmentError) as e:
        # User-facing errors (bad format, missing ffmpeg)
        return jsonify({"error": str(e)}), 400
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Conversion timed out (file may be too large)"}), 504
    except Exception as e:
        return jsonify({"error": f"Conversion failed: {str(e)}"}), 500
    finally:
        # Always clean up the upload
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
        except Exception:
            pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
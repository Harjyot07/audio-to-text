from flask import Flask, request, render_template_string
from pydub import AudioSegment
from faster_whisper import WhisperModel
import os
import time
import tempfile

app = Flask(__name__)

HTML = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="MP3 to text transcription using Whisper AI. Upload MP3 and get transcription instantly.">
  <title>MP3 Recording Transcription</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 40px; }
    .segment { margin-bottom: 10px; }
    .timestamp { color: gray; font-size: 0.9em; }
  </style>
</head>
<body>
  <h1>Bella</h1>
  <form method="post" enctype="multipart/form-data">
    <label for="audio">Upload MP3:</label>
    <input type="file" name="audio" id="audio" accept=".mp3" required>
    <input type="submit" value="Transcribe">
  </form>

  {% if segments %}
    <h2>Transcription ({{ segments|length }} segments):</h2>
    <div>
      {% for seg in segments %}
        <div class="segment">
          <div class="timestamp">[{{ seg.start }} - {{ seg.end }}]</div>
          <div class="text">{{ seg.text }}</div>
        </div>
      {% endfor %}
    </div>
    <h3>Total processing time: {{ processing_time }} seconds</h3>
  {% elif error %}
    <p style="color:red;">{{ error }}</p>
  {% endif %}
</body>
</html>
'''

# Load model once
model = WhisperModel("tiny", device="cpu", compute_type="int8")

def format_timestamp(seconds: float) -> str:
    """Format seconds to HH:MM:SS.mmm"""
    ms = int((seconds - int(seconds)) * 1000)
    s = int(seconds) % 60
    m = (int(seconds) // 60) % 60
    h = int(seconds) // 3600
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

@app.route('/', methods=['GET', 'POST'])
def index():
    segments = []
    processing_time = None
    error = None

    if request.method == 'POST':
        if 'audio' not in request.files:
            error = "No file part"
        else:
            file = request.files['audio']
            if file.filename == '':
                error = "No selected file"
            else:
                try:
                    # Use temporary files to avoid filename conflicts
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_mp3:
                        file.save(temp_mp3.name)
                        mp3_path = temp_mp3.name
                        wav_path = mp3_path.replace(".mp3", ".wav")

                    # Convert MP3 to WAV
                    sound = AudioSegment.from_mp3(mp3_path)
                    sound.export(wav_path, format="wav")

                    # Transcribe
                    start_time = time.time()
                    segments_gen, info = model.transcribe(wav_path, language="en")
                    end_time = time.time()

                    processing_time = round(end_time - start_time, 2)

                    for segment in segments_gen:
                        segments.append({
                            "start": format_timestamp(segment.start),
                            "end": format_timestamp(segment.end),
                            "text": segment.text.strip()
                        })

                except Exception as e:
                    error = f"Error processing file: {e}"
                    print("[ERROR]", e)

                finally:
                    # Clean up temp files
                    try:
                        if os.path.exists(mp3_path):
                            os.remove(mp3_path)
                        if os.path.exists(wav_path):
                            os.remove(wav_path)
                    except Exception as cleanup_error:
                        print("[CLEANUP ERROR]", cleanup_error)

    return render_template_string(HTML, segments=segments, processing_time=processing_time, error=error)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


import io
import json
import time
import wave
from flask import Flask, request, jsonify
from vosk import Model, KaldiRecognizer

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
model = Model('/model')
allowed = {'avanti', 'indietro', 'sinistra', 'destra', 'stop'}

@app.post('/process')
def process():
    # Service starts before body reading; may include waiting for incoming bytes.
    service_start = time.perf_counter()
    raw = request.get_data()
    try:
        with wave.open(io.BytesIO(raw), 'rb') as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getcomptype()) != (1, 2, 16000, 'NONE'):
                raise ValueError('Expected mono PCM16 WAV at 16000 Hz')
            pcm = audio.readframes(audio.getnframes())
            duration = audio.getnframes() / 16000
        start = time.perf_counter()
        recognizer = KaldiRecognizer(model, 16000)
        parts = []
        for offset in range(0, len(pcm), 8000):
            if recognizer.AcceptWaveform(pcm[offset:offset+8000]):
                parts.append(json.loads(recognizer.Result()).get('text', ''))
        parts.append(json.loads(recognizer.FinalResult()).get('text', ''))
        text = ' '.join(p for p in parts if p).strip()
        processing_ms = (time.perf_counter() - start) * 1000
        tokens = text.split()
        result = dict(text=text, commands=[t if t in allowed else 'UNKNOWN' for t in tokens],
                      processing_time_ms=processing_ms, audio_seconds=duration, payload_bytes=len(raw))
        result['service_time_ms'] = (time.perf_counter() - service_start) * 1000
        return jsonify(result)
    except (ValueError, wave.Error, EOFError) as exc:
        return jsonify(error=str(exc)), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5300, threaded=False)

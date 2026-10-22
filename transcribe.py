"""Speech-to-text with faster-whisper. Usage: python transcribe.py clip.wav [hi|en|or]
Reads WAV files itself (no PyAV needed), so it works even if the 'av' package is broken."""
import sys, time, wave
import numpy as np
from faster_whisper import WhisperModel

_model = None
def get_model(size="small"):          # use "base" if your laptop is slow
    global _model
    if _model is None:
        _model = WhisperModel(size, device="cpu", compute_type="int8")
    return _model

def load_wav(path, target_sr=16000):
    """Decode a PCM WAV into mono float32 at 16 kHz using only the stdlib + numpy."""
    with wave.open(path, "rb") as w:
        sr, ch, width, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if width == 2:   data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif width == 4: data = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    elif width == 1: data = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128) / 128.0
    else: raise ValueError("Unsupported WAV format (use 16-bit PCM WAV)")
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    if sr != target_sr:
        t_old = np.linspace(0, 1, len(data), endpoint=False)
        t_new = np.linspace(0, 1, int(len(data) * target_sr / sr), endpoint=False)
        data = np.interp(t_new, t_old, data).astype(np.float32)
    return data

def transcribe(path, language=None):
    """Returns (text, detected_language, avg_confidence). Low confidence => flag for human check."""
    audio = load_wav(path) if path.lower().endswith(".wav") else path
    segs, info = get_model().transcribe(audio, language=language, vad_filter=True, beam_size=5)
    segs = list(segs)
    text = " ".join(s.text.strip() for s in segs)
    conf = round(sum(2.718 ** s.avg_logprob for s in segs) / len(segs), 2) if segs else 0.0
    return text, info.language, conf

if __name__ == "__main__":
    t0 = time.time()
    text, lang, conf = transcribe(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"[{lang} | conf {conf} | {time.time()-t0:.1f}s]\n{text}")

"""Run first: python setup_check.py  -> tells you what is installed and working."""
import shutil, urllib.request, json
def ok(name, good, hint=""): print(("[OK]  " if good else "[FAIL] ") + name + ("" if good else f"  -> {hint}"))

try:
    import faster_whisper; ok("faster-whisper", True)
except ImportError: ok("faster-whisper", False, "pip install faster-whisper")
ok("Tesseract binary", shutil.which("tesseract") is not None, "install Tesseract + hin/ori language packs")
try:
    import pytesseract; ok("pytesseract", True)
except ImportError: ok("pytesseract", False, "pip install pytesseract pillow opencv-python")
try:
    with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as r:
        models = [m["name"] for m in json.loads(r.read())["models"]]
    ok("Ollama running", True); ok("Model pulled (qwen2.5:3b)", any("qwen2.5:3b" in m for m in models), "ollama pull qwen2.5:3b")
except Exception: ok("Ollama running", False, "install from ollama.com, then: ollama serve")
try:
    from extract import extract
    c = extract("fever 3 days, SpO2 91", use_llm=False); ok("rule-based extractor", c["vitals"]["spo2"]["value"] == 91)
except Exception as e: ok("rule-based extractor", False, str(e))

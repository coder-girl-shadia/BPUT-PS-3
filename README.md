# Person A: AI/Data module (Day 1)

## Setup (do first, ~1-2 h)
1. `pip install -r requirements.txt`
2. Tesseract: install the binary + language packs (hin, ori, eng). Windows: UB-Mannheim installer. Linux: `sudo apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-ori`
3. Ollama: install from ollama.com, then `ollama pull qwen2.5:3b` (use `llama3.2:3b` if RAM < 8 GB)
4. `python setup_check.py`  -> all lines should say [OK]
5. First `faster-whisper` run downloads the model (needs internet ONCE). Run it before demo day.

## Record 3 clips (phone voice recorder, WAV/MP3, 15-30 s each)
- clip_hi.wav: Hindi complaint (e.g. P002 text)
- clip_en.wav: English complaint (P001 text)
- clip_maternal.wav: maternal case, e.g. 7 months pregnant, severe headache, blurred vision
Test: `python transcribe.py clip_hi.wav hi`. Keep clips; they are your demo fallback.

## Handoff to Person B (end of day)
    from extract import extract
    case = extract(text, source="voice")   # dict matching schema.py; never raises
Test: `python test_extract.py` (offline rules) and `python test_extract.py --llm` (Ollama).
Whisper: `from transcribe import transcribe; text, lang, conf = transcribe("clip.wav")`
If `conf` < 0.6, tell B to tag the case "needs human check".

All data in fake_patients.py is synthetic. Extraction only: no diagnosis, no risk tags.

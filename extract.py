"""extract(text) -> case dict. Tries local LLM (Ollama); falls back to rule-based extraction.
Extraction ONLY: no diagnosis, no risk tag, no treatment (that is the rules engine's job)."""
import json, re, urllib.request
from schema import empty_case, validate, missing, VITAL_FIELDS

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:3b"   # alternatives: llama3.2:3b, qwen2.5:7b (if RAM allows)

PROMPT = """You are an information extraction tool for a clinic triage form.
Extract ONLY facts explicitly stated in the text. Do NOT diagnose, do NOT suggest treatment,
do NOT guess. If something is not stated, use null (or [] for lists). Text may be English, Hindi or Hinglish.
Return ONLY valid JSON with exactly these keys:
{{"chief_complaint": str|null, "onset": "sudden"|"gradual"|null, "duration": str|null,
 "severity": "mild"|"moderate"|"severe"|null, "symptoms": [str], "history": str|null,
 "pregnancy_status": str|null, "medications": [str], "allergies": str|null,
 "vitals": {{"temp_c": num|null, "spo2": num|null, "pulse": num|null,
            "bp_sys": num|null, "bp_dia": num|null, "resp_rate": num|null}}}}
Use English for all values.
Text: \"\"\"{text}\"\"\"
JSON:"""

# ---------- rule-based fallback (works offline, no model needed) ----------
SYMPTOMS = {
    "fever": ["fever", "bukhar", "bukhaar", "बुखार"],
    "cough": ["cough", "khansi", "khaansi", "खांसी", "खाँसी"],
    "chest pain": ["chest pain", "seene mein dard", "seene me dard", "सीने में दर्द", "सीने मे दर्द"],
    "breathlessness": ["breathless", "shortness of breath", "difficulty breathing", "saans phool", "सांस फूल", "सांस लेने में"],
    "headache": ["headache", "sir dard", "sar dard", "सिरदर्द", "सिर दर्द", "सर दर्द"],
    "vomiting": ["vomit", "ulti", "उल्टी"],
    "diarrhoea": ["diarrh", "loose motion", "dast", "दस्त"],
    "bleeding": ["bleeding", "khoon", "खून"],
    "blurred vision": ["blurred vision", "blurry vision", "dhundhla", "धुंधला"],
    "reduced fetal movement": ["baby not moving", "reduced fetal", "less fetal movement", "baby is not moving",
                               "bacha hil nahi", "बच्चा हिल नहीं", "बच्चा कम हिल"],
    "convulsions": ["convuls", "seizure", "fits", "daura", "दौरे", "झटके", "jhatke"],
    "abdominal pain": ["stomach pain", "abdominal pain", "pet dard", "पेट दर्द", "पेट में दर्द"],
    "weakness": ["weakness", "weak", "kamzori", "कमजोरी"],
    "body ache": ["body ache", "body pain", "badan dard", "बदन दर्द", "बदन में दर्द"],
    "rash": ["rash", "daane", "दाने"],
    "stiff neck": ["stiff neck", "neck stiffness", "गर्दन अकड़"],
    "confusion": ["confus", "drowsy", "unconscious", "behosh", "बेहोश"],
    "swelling": ["swelling", "sujan", "सूजन"],
    "unable to feed": ["not feeding", "unable to feed", "not drinking", "doodh nahi", "दूध नहीं पी"],
}
CONDITIONS = {"diabetes": ["diabetes", "sugar", "शुगर", "मधुमेह"],
              "hypertension": ["hypertension", "high bp", "blood pressure problem", "बीपी"],
              "asthma": ["asthma", "दमा"], "tuberculosis": ["tuberculosis", " tb ", "टीबी"],
              "heart disease": ["heart disease", "heart problem", "दिल की बीमारी"],
              "thyroid": ["thyroid"]}
DRUGS = ["paracetamol", "crocin", "dolo", "ibuprofen", "metformin", "amlodipine", "insulin", "aspirin",
         "azithromycin", "amoxicillin", "iron", "folic acid", "cetirizine", "ors"]
HI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
UNITS = {"day": "day", "days": "days", "din": "days", "दिन": "days", "week": "week", "weeks": "weeks",
         "hafte": "weeks", "हफ्ते": "weeks", "hour": "hour", "hours": "hours", "ghante": "hours",
         "घंटे": "hours", "month": "months", "months": "months", "mahine": "months", "महीने": "months"}

def _f(value, conf, source):
    return {"value": value, "confidence": conf, "source": source}

def rule_extract(text, source="text"):
    t = " " + text.translate(HI_DIGITS).lower() + " "
    case = empty_case(text, source)
    case["meta"]["extractor"] = "rules"

    syms = [name for name, kws in SYMPTOMS.items() if any(k in t for k in kws)]
    case["symptoms"] = _f(syms, 0.75 if syms else 0.0, source)
    if syms:
        case["chief_complaint"] = _f(syms[0], 0.6, source)

    for m in re.finditer(r"(\d+)\s*(days?|din|दिन|weeks?|hafte|हफ्ते|hours?|ghante|घंटे|months?|mahine|महीने)", t):
        if re.match(r"\s*(pregnant|garbh|गर्भ)", t[m.end():]):   # "7 months pregnant" is not a duration
            continue
        case["duration"] = _f(f"{m.group(1)} {UNITS[m.group(2)]}", 0.8, source)
        break

    if re.search(r"sudden|achanak|अचानक", t):
        case["onset"] = _f("sudden", 0.8, source)
    elif re.search(r"gradual|slowly|dheere|धीरे", t):
        case["onset"] = _f("gradual", 0.7, source)

    if re.search(r"severe|very bad|unbearable|bahut tez|bahut jyada|बहुत तेज|बहुत ज्यादा|गंभीर", t):
        case["severity"] = _f("severe", 0.7, source)
    elif re.search(r"moderate|medium|thoda", t):
        case["severity"] = _f("moderate", 0.6, source)
    elif re.search(r"mild|slight|halka|हल्का", t):
        case["severity"] = _f("mild", 0.7, source)

    preg = re.search(r"(\d+)\s*(?:months?|mahine|महीने)\s*(?:pregnant|garbh|गर्भ)", t) or \
           re.search(r"(?:pregnant|garbhwati|गर्भवती|pregnancy)[^.]{0,30}?(\d+)\s*(?:months?|mahine|महीने)", t)
    if preg:
        case["pregnancy_status"] = _f(f"pregnant, {preg.group(1)} months", 0.85, source)
    elif re.search(r"pregnan|garbhwati|गर्भवती|गर्भ", t):
        case["pregnancy_status"] = _f("pregnant", 0.8, source)

    conds = [c for c, kws in CONDITIONS.items() if any(k in t for k in kws)]
    if conds:
        case["history"] = _f(", ".join(conds), 0.7, source)
    meds = [d for d in DRUGS if re.search(rf"\b{d}\b", t)]
    if meds:
        case["medications"] = _f(meds, 0.7, source)
    a = re.search(r"allerg\w*\s+(?:to\s+)?([a-z ]{3,25})", t)
    if a:
        case["allergies"] = _f(a.group(1).strip(), 0.7, source)
    elif re.search(r"no (known )?allerg", t):
        case["allergies"] = _f("none", 0.8, source)

    # vitals
    v = case["vitals"]
    s = re.search(r"(?:spo2|spo₂|oxygen(?: level)?|saturation)\D{0,15}(\d{2,3})", t)
    if s: v["spo2"] = _f(int(s.group(1)), 0.9, source)
    p = re.search(r"(?:pulse|heart rate|hr)\D{0,10}(\d{2,3})", t)
    if p: v["pulse"] = _f(int(p.group(1)), 0.9, source)
    bp = re.search(r"(?:bp|blood pressure)\D{0,10}(\d{2,3})\s*[/ ]\s*(\d{2,3})", t) or re.search(r"(\d{2,3})\s*/\s*(\d{2,3})", t)
    if bp:
        v["bp_sys"] = _f(int(bp.group(1)), 0.9, source); v["bp_dia"] = _f(int(bp.group(2)), 0.9, source)
    r = re.search(r"(?:respiratory rate|resp(?:iratory)? rate|rr)\D{0,10}(\d{2})", t)
    if r: v["resp_rate"] = _f(int(r.group(1)), 0.85, source)
    tm = re.search(r"(?:temp(?:erature)?|fever)\D{0,12}(\d{2,3}(?:\.\d)?)\s*(?:°|degrees?)?\s*(f|c)?", t)
    if tm:
        val = float(tm.group(1)); unit = tm.group(2)
        if (unit == "f") or (val > 45):
            val = round((val - 32) * 5 / 9, 1)
        if 30 <= val <= 45:
            v["temp_c"] = _f(val, 0.9, source)

    # fever can also be inferred from a measured temperature (>= 38 C)
    t_c = case["vitals"]["temp_c"]["value"]
    if t_c is not None and t_c >= 38 and "fever" not in case["symptoms"]["value"]:
        case["symptoms"]["value"].append("fever")
        case["symptoms"]["confidence"] = max(case["symptoms"]["confidence"], 0.8)
    case["meta"]["missing_fields"] = missing(case)
    return case

# ---------- LLM path ----------
def llm_extract(text, source="text", timeout=60):
    body = json.dumps({"model": OLLAMA_MODEL, "prompt": PROMPT.format(text=text),
                       "stream": False, "format": "json",
                       "options": {"temperature": 0}}).encode()
    req = urllib.request.Request(OLLAMA_URL, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = json.loads(r.read())["response"]
    data = json.loads(raw)
    case = validate(data)
    # stamp source + a moderate default confidence on anything the LLM filled
    for f in case:
        if isinstance(case[f], dict) and "value" in case[f] and case[f]["value"] not in (None, [], ""):
            case[f]["confidence"] = 0.7; case[f]["source"] = source
    for k, d in case["vitals"].items():
        if d["value"] is not None: d["confidence"] = 0.8; d["source"] = source
    case["meta"].update({"raw_text": text, "source": source, "extractor": "llm"})
    case["meta"]["missing_fields"] = missing(case)
    return case

def _norm_duration(v):
    """'2 दिन' / '2 ghante' / '1 day' -> canonical '2 days' style, if parseable."""
    if not isinstance(v, str):
        return v
    m = re.search(r"(\d+)\s*([^\d\s]+)", v.translate(HI_DIGITS).lower())
    if m and m.group(2) in UNITS:
        return f"{m.group(1)} {UNITS[m.group(2)]}"
    return v

def _is_english(s):
    return isinstance(s, str) and s.isascii()

def extract(text, source="text", use_llm=True):
    """Main entry point for Person B. Never raises.
    Merge policy (safety-first): RULES win wherever they found a value.
    The LLM only fills gaps. LLM-only symptoms are NOT trusted: they go to
    meta['unverified_symptoms'] for the reviewer and never reach the rules engine."""
    rules_case = rule_extract(text, source)
    if not use_llm:
        return rules_case
    try:
        llm_case = llm_extract(text, source)
    except Exception as e:
        rules_case["meta"]["extractor"] = f"rules (LLM unavailable: {type(e).__name__})"
        return rules_case

    case = rules_case
    case["meta"]["extractor"] = "rules+llm"
    for f in ["chief_complaint", "onset", "duration", "severity", "history",
              "pregnancy_status", "allergies"]:
        if case[f]["value"] in (None, "", []) and llm_case[f]["value"] not in (None, "", []):
            val = llm_case[f]["value"]
            if f == "duration":
                val = _norm_duration(val)
            if f in ("severity", "onset"):
                val = str(val).lower()
                if val not in ("mild", "moderate", "severe", "sudden", "gradual"):
                    continue
            if _is_english(str(val)):   # drop untranslated text rather than store it
                case[f] = {"value": val, "confidence": 0.5, "source": source}
    for k in VITAL_FIELDS:
        if case["vitals"][k]["value"] is None and llm_case["vitals"][k]["value"] is not None:
            case["vitals"][k] = {**llm_case["vitals"][k], "confidence": 0.5}
    known = {x.lower() for x in case["symptoms"]["value"]}
    extras = [x for x in llm_case["symptoms"]["value"]
              if _is_english(x) and not any(k in x.lower() or x.lower() in k for k in known)]
    case["meta"]["unverified_symptoms"] = extras   # reviewer must confirm these
    if not case["symptoms"]["value"] and extras:
        case["meta"]["missing_fields"] = missing(case)
    case["meta"]["missing_fields"] = missing(case)
    return case

if __name__ == "__main__":
    import sys
    print(json.dumps(extract(" ".join(sys.argv[1:]) or "I have fever for 3 days, severe headache, SpO2 92"),
                     indent=2, ensure_ascii=False))
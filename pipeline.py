"""One call for the app: raw text -> masked -> structured case -> triage assessment."""
import time
from pii import mask_pii, pseudo_id
from extract import extract
from rules_engine import assess

def process(text, source="text", known_names=(), use_llm=True, voice_conf=None):
    masked, found = mask_pii(text, known_names)          # PII removed BEFORE any LLM call
    case = extract(masked, source=source, use_llm=use_llm)
    result = assess(case, voice_conf=voice_conf)
    case["meta"]["pii_masked"] = sorted({lbl for lbl, _ in found})
    return {"case_id": pseudo_id(text + str(time.time())), "case": case, "assessment": result}

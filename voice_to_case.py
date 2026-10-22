"""Voice -> transcript -> structured case.  Usage: python voice_to_case.py clip.wav [hi|en] [--llm]"""
import sys, json
from transcribe import transcribe
from extract import extract

args = [a for a in sys.argv[1:] if not a.startswith("--")]
use_llm = "--llm" in sys.argv
path = args[0]
lang = args[1] if len(args) > 1 else None

text, detected, conf = transcribe(path, lang)
print(f"\n1) TRANSCRIPT  [language={detected}, confidence={conf}]\n   {text}")
if conf < 0.6:
    print("   !! LOW CONFIDENCE -> case should be tagged 'needs human check'")

case = extract(text, source="voice", use_llm=use_llm)
print(f"\n2) EXTRACTED   [extractor={case['meta']['extractor']}]")
print(f"   symptoms   : {case['symptoms']['value']}")
for f in ["chief_complaint", "duration", "onset", "severity", "pregnancy_status", "history", "medications", "allergies"]:
    print(f"   {f:<17}: {case[f]['value']}")
print("   vitals     :", {k: v['value'] for k, v in case['vitals'].items() if v['value'] is not None})
print(f"   unverified : {case['meta'].get('unverified_symptoms', [])}")
print(f"   missing    : {case['meta']['missing_fields']}")

with open("last_case.json", "w", encoding="utf-8") as f:
    json.dump(case, f, indent=2, ensure_ascii=False)
print("\n3) Full JSON saved to last_case.json")

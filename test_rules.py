"""python test_rules.py  -> checks tag + PII masking on the 5 synthetic patients, plus safety unit tests."""
from fake_patients import PATIENTS
from pipeline import process
from pii import mask_pii
from rules_engine import assess
from schema import empty_case

GOLD = {"P001": "Urgent", "P002": "Urgent", "P003": "Urgent", "P004": "Routine", "P005": "Urgent"}
ok = 0
for p in PATIENTS:
    r = process(p["text"], use_llm=False)
    tag = r["assessment"]["tag"]; good = tag == GOLD[p["id"]]; ok += good
    raw = r["case"]["meta"]["raw_text"]
    leaked = [x for x in (p["phone"], p["aadhaar"].replace(" ", ""), *p["name"].split()) if len(x) > 3 and x in raw.replace(" ", "")]
    print(f"{p['id']} {'OK  ' if good else 'MISS'} want={GOLD[p['id']]:<8} got={tag:<8} PII leaked={leaked or 'none'}")
    for x in r["assessment"]["reasons"]:
        print(f"      - [{x['tag']}] {x['text']}  ({x['source']})")
print(f"\n{ok}/{len(PATIENTS)} tags correct")

# safety unit tests
c = empty_case(); c["symptoms"]["value"] = ["chest pain", "breathlessness"]
assert assess(c)["tag"] == "Urgent", "chest pain + breathlessness must be Urgent"
c = empty_case(); c["symptoms"]["value"] = ["cough"]; c["vitals"]["spo2"]["value"] = 85
a = assess(c); assert a["tag"] == "Urgent" and a["immediate"], "SpO2 85 must be Urgent+immediate"
c = empty_case(); c["symptoms"]["value"] = ["cough"]; c["meta"]["unverified_symptoms"] = ["dizziness"]
assert assess(c)["tag"] != "Urgent", "unverified LLM symptoms must not drive the tag"
c = empty_case()
assert assess(c)["tag"] == "Priority", "empty case must not be Routine"
t, f = mask_pii("Call 9876501234 or 2345 6789 0123, my name is Asha Mishra")
assert "9876501234" not in t and "2345" not in t and "Asha" not in t and "Mishra" not in t
print("safety unit tests passed")

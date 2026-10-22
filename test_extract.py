"""python test_extract.py [--llm]   (default tests the offline rule extractor)"""
import sys
from extract import extract
from fake_patients import PATIENTS
use_llm = "--llm" in sys.argv
passed = total = 0
for p in PATIENTS:
    c = extract(p["text"], use_llm=use_llm)
    got = {"duration": c["duration"]["value"], "severity": c["severity"]["value"], "onset": c["onset"]["value"],
           "preg": c["pregnancy_status"]["value"], **{k: c["vitals"][k]["value"] for k in c["vitals"]}}
    print(f"\n{p['id']} [{c['meta']['extractor']}] symptoms={c['symptoms']['value']} missing={c['meta']['missing_fields']}")
    for k, want in p["expect"].items():
        total += 1; ok = (got.get(k) == want) or (isinstance(want, float) and got.get(k) and abs(got[k]-want) < 0.2)
        passed += bool(ok); print(f"   {'OK  ' if ok else 'MISS'} {k}: want={want} got={got.get(k)}")
print(f"\n{passed}/{total} checks passed")

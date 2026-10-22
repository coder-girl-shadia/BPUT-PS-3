"""assess(case) -> {tag, reasons, needs_info, immediate, bumped}
Deterministic, escalate-only. The LLM never sets the tag."""
import yaml, os, operator
from schema import missing as find_missing

ORDER = ["Routine", "Priority", "Urgent"]
OPS = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge, "==": operator.eq}
_RULES = None

def load_rules(path=None):
    global _RULES
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules.yaml")
    with open(path, encoding="utf-8") as f:
        _RULES = yaml.safe_load(f)["rules"]
    return _RULES

def _clause(cl, case, syms):
    if "symptom" in cl:       return cl["symptom"].lower() in syms
    if "any_symptom" in cl:   return any(s.lower() in syms for s in cl["any_symptom"])
    if "pregnant" in cl:
        v = (case["pregnancy_status"]["value"] or "").lower()
        return ("pregnan" in v) == cl["pregnant"]
    if "severity" in cl:      return (case["severity"]["value"] or "").lower() == cl["severity"]
    if "vital" in cl:
        v = case["vitals"].get(cl["vital"]["name"], {}).get("value")
        return v is not None and OPS[cl["vital"]["op"]](v, cl["vital"]["value"])
    return False

def _bump(tag):
    return ORDER[min(ORDER.index(tag) + 1, len(ORDER) - 1)]

def assess(case, voice_conf=None, rules=None):
    rules = rules or _RULES or load_rules()
    syms = {s.lower() for s in case["symptoms"]["value"]}
    tag, immediate, reasons, seen = "Routine", False, [], set()
    for r in rules:
        if all(_clause(c, case, syms) for c in r["when"]):
            if ORDER.index(r["tag"]) > ORDER.index(tag):
                tag = r["tag"]
            immediate = immediate or r.get("immediate", False)
            if r["reason"] not in seen:        # avoid duplicate reasons (e.g. BP rules)
                seen.add(r["reason"])
                reasons.append({"rule": r["id"], "tag": r["tag"], "text": r["reason"], "source": r["source"]})
    # multiple symptoms: moderate signal, only ever raises
    if len(syms) >= 3 and tag == "Routine":
        tag = "Priority"
        reasons.append({"rule": "R27", "tag": "Priority", "text": f"{len(syms)} symptoms reported together",
                        "source": "Multiple-symptom signal"})
    # uncertainty handling (escalate-only)
    needs_info, bumped = False, False
    missing = find_missing(case)
    if missing:
        needs_info = True
        reasons.append({"rule": "U1", "tag": "Info", "text": "Missing information: " + ", ".join(missing),
                        "source": "Completeness check"})
    low = [k for k in ("chief_complaint", "duration", "severity")
           if case[k]["value"] is not None and case[k]["confidence"] < 0.5]
    if voice_conf is not None and voice_conf < 0.6:
        low.append("speech transcript")
    if low:
        needs_info = True
        new = _bump(tag)
        bumped = new != tag
        tag = new
        reasons.append({"rule": "U2", "tag": "Info", "text": "Low-confidence input (" + ", ".join(low) + ") - priority raised, needs human check",
                        "source": "Uncertainty handling"})
    if "symptoms" in missing and not case["symptoms"]["value"]:
        if tag == "Routine":
            tag, bumped = "Priority", True
        reasons.append({"rule": "U3", "tag": "Info", "text": "No symptoms captured - cannot be assessed automatically",
                        "source": "Completeness check"})
    unv = case["meta"].get("unverified_symptoms") or []
    if unv:
        needs_info = True
        reasons.append({"rule": "U4", "tag": "Info", "text": "AI-suggested, unverified symptoms for reviewer to confirm: " + ", ".join(unv),
                        "source": "LLM extras (not used for tagging)"})
    rank = {"Urgent": 0, "Priority": 1, "Info": 2}
    reasons.sort(key=lambda x: rank.get(x["tag"], 3))
    return {"tag": tag, "reasons": reasons, "needs_info": needs_info, "immediate": immediate, "bumped": bumped}

if __name__ == "__main__":
    import json, sys
    from extract import extract
    c = extract(" ".join(sys.argv[1:]) or "chest pain and breathlessness, SpO2 91", use_llm=False)
    print(json.dumps(assess(c), indent=2))

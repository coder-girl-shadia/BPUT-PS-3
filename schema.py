"""Shared case schema (agree on this with Person B). Every field = {value, confidence, source}."""
FIELDS = ["chief_complaint", "onset", "duration", "severity", "symptoms",
          "history", "pregnancy_status", "medications", "allergies"]
VITAL_FIELDS = ["temp_c", "spo2", "pulse", "bp_sys", "bp_dia", "resp_rate"]
# Fields the gap detector (Day 2) will treat as essential
REQUIRED = ["chief_complaint", "duration", "severity"]

def empty_field(source="text"):
    return {"value": None, "confidence": 0.0, "source": source}

def empty_case(raw_text="", source="text", language="en"):
    case = {f: empty_field(source) for f in FIELDS}
    case["symptoms"]["value"] = []
    case["medications"]["value"] = []
    case["vitals"] = {v: empty_field(source) for v in VITAL_FIELDS}
    case["meta"] = {"language": language, "source": source, "raw_text": raw_text,
                    "extractor": None, "missing_fields": []}
    return case

def validate(case):
    """Make any dict (e.g. LLM output) conform to the schema; never crash."""
    out = empty_case(case.get("meta", {}).get("raw_text", ""))
    for f in FIELDS:
        v = case.get(f)
        if isinstance(v, dict) and "value" in v:
            out[f]["value"] = v.get("value", out[f]["value"])
            out[f]["confidence"] = float(v.get("confidence", 0.5) or 0)
            out[f]["source"] = v.get("source", "text")
        elif v not in (None, "", []):
            out[f]["value"] = v
            out[f]["confidence"] = 0.5
    for f in ("symptoms", "medications"):
        if not isinstance(out[f]["value"], list):
            out[f]["value"] = [out[f]["value"]] if out[f]["value"] else []
    vit = case.get("vitals", {}) or {}
    for k in VITAL_FIELDS:
        v = vit.get(k)
        if isinstance(v, dict) and "value" in v:
            out["vitals"][k] = {"value": v["value"], "confidence": float(v.get("confidence", 0.5) or 0),
                                "source": v.get("source", "text")}
        elif isinstance(v, (int, float)):
            out["vitals"][k] = {"value": v, "confidence": 0.5, "source": "text"}
    out["meta"].update(case.get("meta", {}))
    out["meta"]["missing_fields"] = missing(out)
    return out

def missing(case):
    m = [f for f in REQUIRED if case[f]["value"] in (None, "", [])]
    if not case["symptoms"]["value"]:
        m.append("symptoms")
    if all(case["vitals"][v]["value"] is None for v in VITAL_FIELDS):
        m.append("vitals")
    return m

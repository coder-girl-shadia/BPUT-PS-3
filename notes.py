"""Reviewer-facing text: summary, follow-up questions, SBAR referral note. Facts only, then guardrail-filtered."""
from guardrail import sanitize

def _v(case, k):
    return case["vitals"][k]["value"]

def vitals_text(case):
    parts = []
    if _v(case, "spo2") is not None: parts.append(f"SpO2 {_v(case, 'spo2')}%")
    if _v(case, "temp_c") is not None: parts.append(f"temperature {_v(case, 'temp_c')} C")
    if _v(case, "pulse") is not None: parts.append(f"pulse {_v(case, 'pulse')}/min")
    if _v(case, "bp_sys") is not None and _v(case, "bp_dia") is not None:
        parts.append(f"BP {_v(case, 'bp_sys')}/{_v(case, 'bp_dia')}")
    if _v(case, "resp_rate") is not None: parts.append(f"resp. rate {_v(case, 'resp_rate')}/min")
    return ", ".join(parts) if parts else "not recorded"

def allowed_terms(case):
    """Patient-reported history/medications/allergies may be repeated as facts."""
    terms = []
    for k in ("history", "allergies"):
        if case[k]["value"]:
            terms += [t.strip() for t in str(case[k]["value"]).split(",")]
    terms += list(case["medications"]["value"])
    return terms

def summary(case):
    syms = ", ".join(case["symptoms"]["value"]) or "no symptoms captured"
    s = f"Patient reports {syms}"
    if case["duration"]["value"]: s += f" for {case['duration']['value']}"
    if case["onset"]["value"]: s += f" (onset: {case['onset']['value']})"
    s += "."
    if case["severity"]["value"]: s += f" Reported severity: {case['severity']['value']}."
    if case["pregnancy_status"]["value"]: s += f" Pregnancy: {case['pregnancy_status']['value']}."
    s += f" Vitals: {vitals_text(case)}."
    if case["history"]["value"]: s += f" Reported history: {case['history']['value']}."
    clean, _ = sanitize(s, allow=allowed_terms(case))
    return clean

# ---- follow-up questions (priority order) ----
Q = {
 "symptoms": ("What is the main problem the patient has?", "मरीज़ को मुख्य रूप से क्या तकलीफ़ है?"),
 "spo2": ("What is the patient's oxygen level (SpO2)?", "मरीज़ का ऑक्सीजन स्तर (SpO2) कितना है?"),
 "temp_c": ("What is the patient's temperature?", "मरीज़ का तापमान कितना है?"),
 "duration": ("How long has this problem been present?", "यह तकलीफ़ कितने समय से है?"),
 "severity": ("How severe is it: mild, moderate or severe?", "तकलीफ़ कितनी गंभीर है: हल्की, मध्यम या तेज़?"),
 "bp": ("What is the patient's blood pressure?", "मरीज़ का ब्लड प्रेशर कितना है?"),
 "pregnancy_status": ("Is the patient pregnant?", "क्या मरीज़ गर्भवती है?"),
 "onset": ("Did it start suddenly or gradually?", "तकलीफ़ अचानक शुरू हुई या धीरे-धीरे?"),
 "pulse": ("What is the patient's pulse?", "नाड़ी (पल्स) कितनी है?"),
 "allergies": ("Does the patient have any known allergies?", "क्या किसी दवा या चीज़ से एलर्जी है?"),
 "medications": ("Which medicines is the patient currently taking?", "मरीज़ अभी कौन-सी दवाइयाँ ले रहा है?"),
 "history": ("Any existing conditions (e.g. diabetes, BP, asthma)?", "क्या पहले से कोई बीमारी है (जैसे शुगर, बीपी, दमा)?"),
}
ORDER = ["symptoms", "spo2", "temp_c", "duration", "severity", "bp", "pregnancy_status", "onset", "pulse",
         "allergies", "medications", "history"]

def questions(case, lang="en", n=5):
    missing = []
    for k in ORDER:
        if k == "symptoms": empty = not case["symptoms"]["value"]
        elif k == "bp": empty = _v(case, "bp_sys") is None
        elif k in ("spo2", "temp_c", "pulse"): empty = _v(case, k) is None
        elif k == "medications": empty = not case["medications"]["value"]
        else: empty = case[k]["value"] in (None, "")
        if empty: missing.append(k)
    i = 1 if lang == "hi" else 0
    return [Q[k][i] for k in missing[:n]]

def sbar(case, assessment, case_id, final_tag=None, status="New"):
    tag = final_tag or assessment["tag"]
    flags = "; ".join(r["text"] for r in assessment["reasons"] if r["tag"] in ("Urgent", "Priority")) or "none"
    txt = f"""REFERRAL NOTE (SBAR) - DRAFT FOR CLINICIAN SIGN-OFF
Case ID: {case_id} (pseudonymous)   Reviewer tag: {tag}   Status: {status}

S - SITUATION
{summary(case)}

B - BACKGROUND
Reported history: {case['history']['value'] or 'not recorded'}
Reported medications: {', '.join(case['medications']['value']) or 'not recorded'}
Reported allergies: {case['allergies']['value'] or 'not recorded'}
Pregnancy: {case['pregnancy_status']['value'] or 'not recorded'}

A - ASSESSMENT OF DATA (not a diagnosis)
Vitals: {vitals_text(case)}
Triage-support flags raised: {flags}
Missing information: {', '.join(case['meta'].get('missing_fields', [])) or 'none'}

R - REQUEST
Clinical evaluation and review by the receiving facility is requested.

Educational prototype - triage support only. Not a medical device. Contains no diagnosis or treatment advice."""
    clean, v = sanitize(txt, allow=allowed_terms(case))
    return clean, v

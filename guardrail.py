"""Output guardrail: blocks diagnosis / treatment language in any generated text.
sanitize(text, allow=[...]) -> (clean_text, violations).  `allow` = patient-REPORTED terms (history, meds)
that may be repeated as facts."""
import re

DRUGS = ["paracetamol", "acetaminophen", "crocin", "dolo", "ibuprofen", "aspirin", "metformin", "amlodipine",
         "insulin", "azithromycin", "amoxicillin", "doxycycline", "ciprofloxacin", "antibiotic", "antibiotics",
         "steroid", "ors", "tablet", "tablets", "syrup", "injection", "capsule", "cetirizine"]
DIAGNOSES = ["dengue", "malaria", "typhoid", "pneumonia", "covid", "covid-19", "stroke", "heart attack",
             "myocardial infarction", "preeclampsia", "pre-eclampsia", "eclampsia", "meningitis", "sepsis",
             "appendicitis", "cholera", "jaundice", "hepatitis"]
PHRASES = [
    r"\byou (?:have|are suffering|probably have|might have|may have)\b",
    r"\b(?:the )?patient (?:has|is suffering from|probably has|likely has)\s+(?:a |an )?[a-z\-]+\b(?= (?:infection|disease|fever|attack))",
    r"\bdiagnos(?:is|ed|e)\b", r"\bsuffering from\b", r"\blikely (?:has|have|suffering)\b",
    r"\bprescrib\w*\b", r"\bshould (?:take|be given|start|receive)\b", r"\badminister\w*\b",
    r"\b(?:recommend(?:ed)?|advise[d]?|suggest(?:ed)?) (?:treatment|medication|medicine|drug|therapy)\b",
    r"\bstart (?:him|her|the patient|patient) on\b", r"\btake (?:this|the|one|two|a) (?:medicine|medication|drug|tablet)\b",
]
DOSE = re.compile(r"\b\d+(?:\.\d+)?\s?(?:mg|mcg|µg|ml|iu|units?|g)\b", re.I)
REPLACEMENT = "[removed: safety filter]"

def _compile():
    pats = [re.compile(r"\b" + re.escape(w) + r"\b", re.I) for w in DRUGS + DIAGNOSES]
    pats += [re.compile(p, re.I) for p in PHRASES] + [DOSE]
    return pats
_PATS = _compile()

def sanitize(text, allow=()):
    allow_l = {a.lower() for a in allow}
    violations, out = [], text
    for p in _PATS:
        def repl(m):
            if m.group(0).lower() in allow_l:
                return m.group(0)
            violations.append(m.group(0))
            return REPLACEMENT
        out = p.sub(repl, out)
    return out, violations

def check(text, allow=()):
    return sanitize(text, allow)[1]

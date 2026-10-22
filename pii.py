"""PII masking. Run BEFORE any text reaches an LLM. mask_pii(text, known_names=[]) -> (masked, found)"""
import re

PATTERNS = [
    ("AADHAAR", re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b")),
    ("PHONE",   re.compile(r"(?<!\d)(?:\+91[ -]?|0)?[6-9]\d{9}(?!\d)")),
    ("EMAIL",   re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
]
# cue phrases: "my name is X", "mera naam X hai", "baby of X", "mera naam" in Devanagari
NAME_CUES = [
    re.compile(r"(?i)\b(?:my name is|i am|i'm|name is|patient name[: ]+)\s+((?:[A-Z][a-z]+)(?:\s+[A-Z][a-z]+){0,3})"),
    re.compile(r"(?i)\b(?:mera naam|meri naam|mera name|naam)\s+((?:[A-Z][a-z]+)(?:\s+[A-Z][a-z]+){0,3})"),
    re.compile(r"(?i)\b(?:baby of|son of|daughter of|student|mr\.?|mrs\.?|ms\.?|smt\.?|shri)\s+((?:[A-Z][a-z]+)(?:\s+[A-Z][a-z]+){0,3})"),
    re.compile(r"(?:मेरा नाम|नाम)\s+([\u0900-\u097F]+(?:\s+[\u0900-\u097F]+)?)\s+(?:है|हैं)"),
]
STOP = {"have", "having", "feeling", "very", "not", "pregnant", "sick", "here", "a", "the", "in", "from"}

def mask_pii(text, known_names=()):
    found, out = [], text
    for label, pat in PATTERNS:
        for m in pat.finditer(out):
            found.append((label, m.group(0)))
        out = pat.sub(f"[{label}]", out)
    names = set(known_names)
    for pat in NAME_CUES:
        for m in pat.finditer(out):
            n = m.group(1).strip()
            if n.split()[0].lower() not in STOP:
                names.add(n)
    for n in sorted(names, key=len, reverse=True):
        for part in [n] + [p for p in n.split() if len(p) > 2]:   # also mask first/last name alone
            if part in out:
                found.append(("NAME", part))
                out = out.replace(part, "[NAME]")
    return out, found

def pseudo_id(seed):
    import hashlib
    return "C-" + hashlib.sha256(str(seed).encode()).hexdigest()[:8].upper()

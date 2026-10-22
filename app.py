"""Multimodal Healthcare Triage Assistant - EDUCATIONAL PROTOTYPE.  Run:  streamlit run app.py
AI organizes. Rules flag. Humans decide."""
import os, time, json, tempfile
import streamlit as st
import db, notes
from pipeline import process
from pii import mask_pii
from guardrail import sanitize

st.set_page_config(page_title="Triage Support (Prototype)", page_icon="🩺", layout="wide")
db.init()
for _id in db.purge_expired():
    pass

# ── NovaCare Design System (from Stitch) ─────────────────────────
st.markdown("""
<style>
/* ── Google Fonts (graceful fallback if offline) ── */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

:root {
    --nc-primary: #0D5C75;
    --nc-secondary: #028090;
    --nc-tertiary: #10B981;
    --nc-neutral: #334155;
    --nc-bg: #EEF3FF;
    --nc-card: #E1EAFF;
    --nc-surface: #FFFFFF;
    --nc-radius: 14px;
    --nc-font-heading: "Plus Jakarta Sans", "Inter", system-ui, sans-serif;
    --nc-font-body: "Inter", "Plus Jakarta Sans", system-ui, sans-serif;
}

/* ── Global typography ── */
html, body, [class*="st-"] {
    font-family: var(--nc-font-body) !important;
}
h1, h2, h3, h4, h5, h6,
[data-testid="stHeadingWithActionElements"] {
    font-family: var(--nc-font-heading) !important;
    color: var(--nc-primary) !important;
    font-weight: 700 !important;
}
p, li, span, label, td, th, div {
    font-family: var(--nc-font-body) !important;
}

/* ── Sidebar: deep medical cyan ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0A475B 0%, var(--nc-primary) 100%) !important;
}
section[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stTextInput label,
section[data-testid="stSidebar"] .stRadio label,
section[data-testid="stSidebar"] .stCheckbox label {
    color: rgba(255,255,255,0.92) !important;
}
section[data-testid="stSidebar"] [data-testid="stCaption"] {
    color: rgba(255,255,255,0.70) !important;
}
section[data-testid="stSidebar"] .stSelectbox > div > div,
section[data-testid="stSidebar"] .stTextInput > div > div > input {
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    color: #FFFFFF !important;
    border-radius: 8px !important;
}

/* ── Cards & containers: soft blue, rounded ── */
[data-testid="stExpander"],
[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"],
div.stTabs [data-baseweb="tab-panel"] {
    border-radius: var(--nc-radius) !important;
}
[data-testid="stExpander"] {
    background: var(--nc-surface) !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: var(--nc-radius) !important;
    box-shadow: 0 2px 4px rgba(15,23,42,0.04) !important;
}

/* ── Primary buttons ── */
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"],
.stDownloadButton > button {
    background: var(--nc-primary) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: var(--nc-font-heading) !important;
    font-weight: 600 !important;
    padding: 0.55rem 1.4rem !important;
    transition: background 0.15s ease !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover,
.stDownloadButton > button:hover {
    background: #0A475B !important;
}

/* ── Secondary / default buttons: outlined ── */
.stButton > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]) {
    background: transparent !important;
    color: var(--nc-primary) !important;
    border: 1.5px solid var(--nc-primary) !important;
    border-radius: 10px !important;
    font-family: var(--nc-font-heading) !important;
    font-weight: 600 !important;
    transition: all 0.15s ease !important;
}
.stButton > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]):hover {
    background: rgba(13,92,117,0.08) !important;
}

/* ── Tabs styling ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px 10px 0 0 !important;
    font-family: var(--nc-font-heading) !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
}
.stTabs [aria-selected="true"] {
    color: var(--nc-primary) !important;
    border-bottom: 3px solid var(--nc-primary) !important;
}

/* ── Dataframe & table ── */
[data-testid="stDataFrame"] {
    border-radius: var(--nc-radius) !important;
    overflow: hidden !important;
    border: 1px solid #CBD5E1 !important;
}

/* ── Text area & inputs ── */
.stTextArea textarea, .stTextInput input {
    border-radius: 10px !important;
    border: 1px solid #CBD5E1 !important;
    font-family: var(--nc-font-body) !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--nc-secondary) !important;
    box-shadow: 0 0 0 2px rgba(2,128,144,0.15) !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
    border-radius: 10px !important;
}

/* ── Dividers ── */
hr {
    border-color: #CBD5E1 !important;
    opacity: 0.5 !important;
}

/* ── Disclaimer & Emergency banners: keep high visibility ── */
.stAlert [data-testid="stAlertContentWarning"],
[data-testid="stAlert"] {
    border-radius: 10px !important;
}

/* ── Metric display ── */
[data-testid="stMetricValue"] {
    font-family: var(--nc-font-heading) !important;
    font-weight: 700 !important;
    color: var(--nc-primary) !important;
}

/* ── Page title area ── */
.appview-container .main .block-container {
    padding-top: 2rem !important;
}

/* ── Scrollbar styling ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: #94A3B8;
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover { background: #64748B; }
</style>
""", unsafe_allow_html=True)

DISCLAIMER = ("⚠️ Educational prototype for triage-support only. Not a medical device. It does not diagnose or "
              "recommend treatment. All output is advisory and must be reviewed by a qualified professional. "
              "Synthetic data only.")
EMERGENCY = "🚨 If there is severe chest pain, difficulty breathing, convulsions, heavy bleeding or unconsciousness: call 108 / go to the nearest emergency facility now."
ICON = {"Urgent": "🔴", "Priority": "🟠", "Routine": "🟢"}
SLA_MIN = {"Urgent": 15, "Priority": 60, "Routine": 240}   # mock SLA targets (minutes)

CONSENT = {
 "en": "I consent to my symptoms (text/voice) being processed to prepare a triage note for a qualified health professional. "
       "Personal identifiers (name, phone, Aadhaar) are masked before processing. Data is kept for only {ttl} and then "
       "deleted automatically. This is an educational prototype, not medical advice.",
 "hi": "मैं सहमति देता/देती हूँ कि मेरे लक्षणों (टेक्स्ट/आवाज़) को योग्य स्वास्थ्य कर्मी के लिए ट्राइएज नोट बनाने हेतु प्रोसेस किया जाए। "
       "नाम, फोन, आधार जैसी पहचान जानकारी प्रोसेसिंग से पहले छिपा दी जाती है। डेटा केवल {ttl} रखा जाएगा और फिर अपने-आप हटा दिया जाएगा। "
       "यह केवल शैक्षिक प्रोटोटाइप है, चिकित्सकीय सलाह नहीं।",
}

def fmt_dur(sec):
    sec = max(0, int(sec))
    if sec < 90: return f"{sec}s"
    if sec < 5400: return f"{sec // 60} min"
    return f"{sec / 3600:.1f} h"

# ---------------- sidebar: mock login / RBAC ----------------
st.sidebar.title("🩺 Triage Support")
role = st.sidebar.selectbox("Role (mock login)", ["Health worker", "Doctor", "Admin"])
user = st.sidebar.text_input("User name", {"Health worker": "ASHA-01", "Doctor": "Dr-Demo", "Admin": "admin"}[role])
lang = st.sidebar.radio("Language / भाषा", ["en", "hi"], format_func=lambda x: "English" if x == "en" else "हिन्दी")
use_llm = st.sidebar.checkbox("Use local LLM (Ollama)", value=False,
                              help="Off = rules only (fastest, fully offline). On = rules + LLM extras.")
actor = f"{role}:{user}"
ttl_min = float(db.get_setting("ttl_minutes", "1440"))
st.sidebar.caption(f"Data retention: {fmt_dur(ttl_min * 60)}, then auto-deleted")
_all = db.list_cases()
pend_n = sum(1 for c in _all if c["status"] == "Info requested")
new_n = sum(1 for c in _all if c["status"] == "New")
if role == "Health worker" and pend_n:
    st.sidebar.error(f"📬 {pend_n} case(s) waiting for information from you")
if role == "Doctor":
    st.sidebar.info(f"📋 {new_n} awaiting review · {pend_n} awaiting info")

st.warning(DISCLAIMER)

def render_flags(a):
    st.markdown(f"### {ICON[a['tag']]} System tag: **{a['tag']}**" + ("  ·  ⏱ IMMEDIATE REVIEW" if a["immediate"] else ""))
    if a["needs_info"]: st.info("ℹ️ Incomplete or uncertain input - needs human check")
    st.markdown("**Why flagged:**")
    for r in a["reasons"]:
        st.markdown(f"- {ICON.get(r['tag'], 'ℹ️')} {r['text']}  \n  <small>source: {r['source']}</small>", unsafe_allow_html=True)

# ---------------- health worker ----------------
def do_transcribe(audio, code):
    try:
        from transcribe import transcribe
    except Exception as e:
        st.session_state.t_err = f"Speech-to-text not available ({type(e).__name__}). Please type the complaint."
        return
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio.getvalue()); path = f.name
        text, det, conf = transcribe(path, None if code == "auto" else code)
        os.unlink(path)
        st.session_state.case_text = text
        st.session_state.voice_conf = conf
        st.session_state.src = "voice"
        st.session_state.t_err = "" if conf >= 0.6 else f"Low speech confidence ({conf}). Please check the transcript carefully."
    except Exception as e:
        st.session_state.t_err = f"Could not transcribe ({type(e).__name__}: {e}). Please type the complaint."

def pending_info_panel():
    pend = [c for c in db.list_cases() if c["status"] == "Info requested"]
    if not pend: return
    st.warning(f"📬 {len(pend)} case(s) need more information from you")
    for c in pend:
        with st.expander(f"{ICON[c['effective_tag']]} {c['id']} - the reviewer needs more information", expanded=True):
            req = [m for m in db.get_messages(c["id"]) if m["kind"] == "info_request"]
            if req:
                st.markdown("**Reviewer's request:**"); st.info(req[-1]["text"])
            st.caption("Current summary: " + notes.summary(c["case"]))
            new = st.text_area("Type the missing information collected from the patient", key=f"add_{c['id']}")
            if st.button("Submit additional info", key=f"sub_{c['id']}"):
                if not new.strip():
                    st.error("Please type the information first.")
                else:
                    masked_new, _ = mask_pii(new)
                    combined = c["text_masked"] + "\n[Additional info] " + masked_new
                    res = process(combined, source="text", use_llm=use_llm)
                    db.update_after_info(c["id"], combined, res["case"], res["assessment"])
                    db.add_message(c["id"], actor, "info_added", masked_new)
                    db.add_audit(actor, "INFO_ADDED", c["id"], f"new_system_tag={res['assessment']['tag']}")
                    st.rerun()

def hw_view():
    st.error(EMERGENCY)
    ss = st.session_state
    pending_info_panel()
    if ss.get("last"):
        res = ss.last
        st.success(f"Sent to reviewer queue. Case ID: **{res['case_id']}**")
        render_flags(res["assessment"])
        qs = notes.questions(res["case"], lang)
        if qs:
            st.markdown("**Please ask the patient / check:**")
            for q in qs: st.markdown(f"- {q}")
        if st.button("➕ Start new patient"):
            ss.last = None; st.rerun()
        return
    st.subheader("New patient" if lang == "en" else "नया मरीज़")
    if not ss.get("consent_id"):
        st.info(CONSENT[lang].format(ttl=fmt_dur(ttl_min * 60)))
        ok = st.checkbox("Patient has given consent / मरीज़ ने सहमति दी है")
        if st.button("Record consent", disabled=not ok, type="primary"):
            ss.consent_id = db.log_consent(actor, lang, ttl_min); st.rerun()
        return
    st.caption(f"✅ Consent recorded (#{ss.consent_id})")
    if ss.pop("clear_text", False):          # must happen BEFORE the text_area is created
        ss["case_text"] = ""
    ss.setdefault("case_text", ""); ss.setdefault("src", "text"); ss.setdefault("voice_conf", None)
    tab_t, tab_v = st.tabs(["⌨️ Type", "🎤 Voice"])
    with tab_v:
        code = st.selectbox("Spoken language", ["hi", "en", "auto"], format_func={"hi": "Hindi", "en": "English", "auto": "Auto-detect"}.get)
        audio = st.audio_input("Record") if hasattr(st, "audio_input") else None
        up = st.file_uploader("...or upload a WAV file", type=["wav"])
        src_audio = audio or up
        if src_audio is not None:
            st.audio(src_audio)
            st.button("Transcribe", on_click=do_transcribe, args=(src_audio, code))
        if ss.get("t_err"): st.warning(ss.t_err)
    with tab_t:
        st.caption("Describe symptoms, duration and any vitals (SpO2, temperature, BP, pulse). Hindi, English or Hinglish.")
    text = st.text_area("Patient complaint (editable)", key="case_text", height=140)
    name = st.text_input("Patient name (optional - used only to mask it)")
    if st.button("Analyze & send to reviewer", type="primary", disabled=not text.strip()):
        res = process(text, source=ss.src, known_names=[name] if name.strip() else [], use_llm=use_llm,
                      voice_conf=ss.voice_conf if ss.src == "voice" else None)
        masked = res["case"]["meta"]["raw_text"]
        db.save_case(res["case_id"], ss.src, masked, res["case"], res["assessment"], ttl_min,
                     ss.voice_conf if ss.src == "voice" else None, ss.consent_id)
        db.add_audit(actor, "CASE_CREATED", res["case_id"],
                     f"source={ss.src}, system_tag={res['assessment']['tag']}, pii_masked={res['case']['meta']['pii_masked']}")
        ss.last = res; ss.consent_id = None; ss.clear_text = True; ss.src = "text"; ss.voice_conf = None; ss.t_err = ""
        st.rerun()

# ---------------- doctor ----------------
def dr_view():
    cases = db.list_cases()
    st.subheader("Reviewer queue")
    if not cases:
        st.info("No cases in the queue. Add one as a Health worker, or load demo patients in the Admin tab."); return
    now = time.time()
    rows = []
    for c in cases:
        wait = now - c["created"]
        breach = c["status"] == "New" and wait > SLA_MIN[c["effective_tag"]] * 60
        rows.append({"Case": c["id"], "Tag": f"{ICON[c['effective_tag']]} {c['effective_tag']}", "Status": c["status"],
                     "Waiting": fmt_dur(wait), "SLA": "⚠️ breached - escalate to MO" if breach else "ok",
                     "Deletes in": fmt_dur(c["expires"] - now)})
    st.dataframe(rows, use_container_width=True, hide_index=True)
    ids = [c["id"] for c in cases]
    sel = st.selectbox("Open case", ids)
    c = db.get_case(sel)
    if not c:
        st.warning("Case no longer exists (retention period ended)."); return
    if st.session_state.get("viewed") != sel:
        db.add_audit(actor, "VIEW_CASE", sel, ""); st.session_state.viewed = sel
    case, a = c["case"], c["assessment"]
    st.divider()
    left, right = st.columns([3, 2])
    with left:
        eff = c["effective_tag"]
        st.markdown(f"## {ICON[eff]} {sel}  ·  {eff}  ·  _{c['status']}_")
        if c["final_tag"] and c["final_tag"] != c["tag"]:
            st.caption(f"System tag was **{c['tag']}**; reviewer set **{c['final_tag']}**.")
        render_flags(a)
        st.markdown("**Summary (advisory)**"); st.write(notes.summary(case))
        qs = notes.questions(case, lang)
        if qs:
            st.markdown("**Follow-up questions for the health worker:**")
            for q in qs: st.markdown(f"- {q}")
    with right:
        st.markdown("**Extracted fields**")
        flds = [{"Field": k, "Value": str(case[k]["value"]), "Conf": case[k]["confidence"], "Source": case[k]["source"]}
                for k in ["chief_complaint", "duration", "onset", "severity", "symptoms", "history", "pregnancy_status", "medications", "allergies"]]
        flds += [{"Field": f"vital: {k}", "Value": str(v["value"]), "Conf": v["confidence"], "Source": v["source"]}
                 for k, v in case["vitals"].items() if v["value"] is not None]
        st.dataframe(flds, hide_index=True, use_container_width=True)
        unv = case["meta"].get("unverified_symptoms")
        if unv: st.warning("AI-suggested, UNVERIFIED (not used for tagging): " + ", ".join(unv))
        with st.expander("Original input (PII masked)"):
            st.write(c["text_masked"])
            st.caption(f"source: {c['source']}  ·  extractor: {case['meta'].get('extractor')}  ·  PII masked: {case['meta'].get('pii_masked')}"
                       + (f"  ·  speech confidence: {c['voice_conf']}" if c["voice_conf"] is not None else ""))
    thread = db.get_messages(sel)
    if thread:
        with st.expander(f"💬 Messages ({len(thread)})", expanded=(c["status"] == "Info requested")):
            for m in thread:
                who = "Reviewer → health worker" if m["kind"] == "info_request" else "Health worker → reviewer (added info)"
                st.markdown(f"**{who}** · {time.strftime('%H:%M', time.localtime(m['ts']))}")
                st.write(m["text"])
    st.markdown("### Reviewer actions")
    b1, b2 = st.columns(2)
    if b1.button("✅ Confirm tag"):
        db.set_status(sel, "Confirmed", final_tag=c["tag"]); db.add_audit(actor, "CONFIRM", sel, f"tag={c['tag']}"); st.rerun()
    if b2.button("⬆️ Escalate to Urgent"):
        db.set_status(sel, "Escalated", final_tag="Urgent"); db.add_audit(actor, "ESCALATE", sel, f"from={eff}"); st.rerun()
    with st.expander("❓ Request more info from the health worker", expanded=(c["status"] == "Info requested")):
        default = "\n".join(f"- {qe} / {qh}" for qe, qh in zip(notes.questions(case, "en"), notes.questions(case, "hi")))
        msg = st.text_area("Message to health worker (what should be collected?)", value=default, key=f"req_{sel}")
        if st.button("Send request to health worker"):
            if not msg.strip(): st.error("Please write what information is needed.")
            else:
                db.add_message(sel, actor, "info_request", msg.strip())
                db.set_status(sel, "Info requested")
                db.add_audit(actor, "REQUEST_INFO", sel, msg.strip()[:200]); st.rerun()
    with st.expander("✏️ Override tag (reason required)"):
        new = st.selectbox("New tag", ["Routine", "Priority", "Urgent"], index=["Routine", "Priority", "Urgent"].index(eff))
        reason = st.text_area("Reason (mandatory)")
        if st.button("Apply override"):
            if not reason.strip(): st.error("A reason is required to override.")
            else:
                db.set_status(sel, "Overridden", final_tag=new)
                db.add_audit(actor, "OVERRIDE", sel, f"{eff} -> {new}; reason: {reason.strip()}"); st.rerun()
    with st.expander("📄 Referral note (SBAR) - needs sign-off"):
        note, viol = notes.sbar(case, a, sel, c["final_tag"], c["status"])
        st.text(note)
        if viol: st.caption(f"Safety filter removed {len(viol)} disallowed phrase(s).")
        signed = st.checkbox("I have reviewed this note and approve it for export")
        who = st.text_input("Reviewer name for sign-off")
        st.download_button("⬇️ Export referral note", note, file_name=f"referral_{sel}.txt",
                           disabled=not (signed and who.strip()),
                           on_click=lambda: db.add_audit(actor, "EXPORT_REFERRAL", sel, f"signed_by={who}"))

# ---------------- admin ----------------
DEMO = [
 "I have had high fever for 3 days with severe headache and vomiting. Temperature 102 F, SpO2 93, pulse 104. I have diabetes. Taking paracetamol.",
 "मैं 7 महीने गर्भवती हूँ। 2 दिन से बहुत तेज सिरदर्द है और धुंधला दिखाई दे रहा है। बीपी 150/100।",
 "Seene mein dard hai aur saans phoolna 2 ghante se, achanak shuru hua. Pulse 118, oxygen 89.",
 "Mild cough and body ache since 1 day. Temperature 99.5 F. Allergic to penicillin.",
 "Mere bacche ko kal se bukhar hai aur jhatke aa rahe hain, doodh nahi pi raha. Temperature 103 F.",
]
def admin_view():
    st.subheader("Admin")
    c1, c2 = st.columns(2)
    with c1:
        v = st.number_input("Data retention (minutes)", 1.0, 100000.0, ttl_min, help="Use 2 to demo auto-delete")
        if st.button("Save retention"):
            db.set_setting("ttl_minutes", v); db.add_audit(actor, "SET_RETENTION", "", f"{v} min"); st.rerun()
        if st.button("Load 5 synthetic demo patients"):
            for t in DEMO:
                r = process(t, use_llm=False)
                db.save_case(r["case_id"], "text", r["case"]["meta"]["raw_text"], r["case"], r["assessment"], ttl_min)
                db.add_audit(actor, "CASE_CREATED", r["case_id"], f"demo, system_tag={r['assessment']['tag']}")
            st.rerun()
    with c2:
        if st.button("🔍 Verify audit-log integrity"):
            ok, bad = db.verify_audit()
            st.success("Audit chain intact ✅") if ok else st.error(f"Audit chain BROKEN at entry #{bad}")
        if st.button("🗑 Reset demo data (all)"):
            db.reset_all(); st.rerun()
    st.markdown("**Audit log (newest first)**")
    rows = db.audit_rows()
    for r in rows: r["ts"] = time.strftime("%H:%M:%S", time.localtime(r["ts"])); r["hash"] = r["hash"][:10]; r.pop("prev_hash")
    st.dataframe(rows, hide_index=True, use_container_width=True)

if role == "Health worker": hw_view()
elif role == "Doctor": dr_view()
else: admin_view()

st.divider()
st.caption(DISCLAIMER)

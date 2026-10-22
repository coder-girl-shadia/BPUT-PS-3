"""python test_app_logic.py -> tests audit chain, retention, guardrail, notes (no Streamlit needed)."""
import os, tempfile, time, sqlite3
os.environ["TRIAGE_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
import db, notes
from guardrail import sanitize
from pipeline import process

db.init()
# audit chain
db.add_audit("Doctor:x", "VIEW_CASE", "C-1", ""); db.add_audit("Doctor:x", "OVERRIDE", "C-1", "Urgent -> Routine; reason: test")
assert db.verify_audit() == (True, None)
with sqlite3.connect(db.DB) as c: c.execute("UPDATE audit SET detail='tampered' WHERE id=1")
ok, bad = db.verify_audit(); assert not ok and bad == 1, "tampering must be detected"
print("audit chain: tamper detected OK")
# queue order + retention
db.reset_all()
for t in ["mild cough 1 day", "chest pain and breathlessness 2 hours SpO2 88", "fever 3 days severe"]:
    r = process(t, use_llm=False); db.save_case(r["case_id"], "text", r["case"]["meta"]["raw_text"], r["case"], r["assessment"], 0.02)
tags = [c["effective_tag"] for c in db.list_cases()]; print("queue order:", tags); assert tags[0] == "Urgent"
time.sleep(1.5); gone = db.purge_expired(); assert len(gone) == 3 and not db.list_cases(); print("auto-delete OK:", len(gone), "cases purged")
assert db.verify_audit()[0]
# guardrail
bad_text = "You have dengue. Take paracetamol 500 mg twice daily. I diagnosed pneumonia and prescribe an antibiotic."
clean, v = sanitize(bad_text); print("guardrail removed:", v); assert not any(w in clean.lower() for w in ["dengue", "paracetamol", "500 mg", "pneumonia", "prescribe", "you have"])
ok_text, v2 = sanitize("Patient reports fever and takes paracetamol.", allow=["paracetamol"]); assert "paracetamol" in ok_text
# notes
r = process("My name is Asha Mishra, 9876501234. Fever for 3 days, SpO2 91. Taking paracetamol.", use_llm=False)
note, viol = notes.sbar(r["case"], r["assessment"], r["case_id"]); assert "Asha" not in note and "9876501234" not in note
assert "paracetamol" in note  # patient-reported medication kept as fact
print("questions (en):", notes.questions(r["case"])[:3]); print("questions (hi):", notes.questions(r["case"], "hi")[:2])
# info-request loop: doctor asks -> worker adds info -> case returns to queue, escalate-only
db.reset_all(); db.init()
r = process("mild cough 1 day", use_llm=False)
db.save_case("C-LOOP", "text", r["case"]["meta"]["raw_text"], r["case"], r["assessment"], 60)
db.set_status("C-LOOP", "Overridden", final_tag="Routine")          # reviewer had set Routine
db.add_message("C-LOOP", "Doctor:x", "info_request", "Please check SpO2 and chest symptoms")
db.set_status("C-LOOP", "Info requested")
c = db.get_case("C-LOOP"); assert c["status"] == "Info requested"
combined = c["text_masked"] + "\n[Additional info] chest pain and breathlessness, SpO2 88"
r2 = process(combined, use_llm=False)
db.update_after_info("C-LOOP", combined, r2["case"], r2["assessment"])
db.add_message("C-LOOP", "Health worker:y", "info_added", "chest pain and breathlessness, SpO2 88")
c = db.get_case("C-LOOP")
assert c["status"] == "New" and c["effective_tag"] == "Urgent", "new danger signs must override old Routine tag"
assert [m["kind"] for m in db.get_messages("C-LOOP")] == ["info_request", "info_added"]
print("info-request loop OK: case returned to queue as", c["effective_tag"])
print("\nALL APP-LOGIC TESTS PASSED")

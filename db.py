"""SQLite storage: cases (masked data only, with expiry), consent log, hash-chained audit log."""
import sqlite3, json, time, hashlib, os

DB = os.environ.get("TRIAGE_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "triage.db"))

def _c():
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    return c

def init():
    with _c() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS cases(
            id TEXT PRIMARY KEY, created REAL, expires REAL, source TEXT, text_masked TEXT,
            case_json TEXT, assessment_json TEXT, tag TEXT, final_tag TEXT, status TEXT,
            voice_conf REAL, consent_id INTEGER);
        CREATE TABLE IF NOT EXISTS consent(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, actor TEXT, language TEXT, ttl_minutes REAL);
        CREATE TABLE IF NOT EXISTS audit(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, actor TEXT, action TEXT, case_id TEXT,
            detail TEXT, prev_hash TEXT, hash TEXT);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, ts REAL, actor TEXT, kind TEXT, text TEXT);
        """)

def get_setting(key, default):
    with _c() as c:
        r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default

def set_setting(key, value):
    with _c() as c:
        c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (key, str(value)))

# ---------- audit (append-only, hash-chained) ----------
def _hash(prev, ts, actor, action, case_id, detail):
    return hashlib.sha256(f"{prev}|{ts}|{actor}|{action}|{case_id}|{detail}".encode()).hexdigest()

def add_audit(actor, action, case_id="", detail=""):
    with _c() as c:
        r = c.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
        prev = r["hash"] if r else "GENESIS"
        ts = round(time.time(), 3)
        h = _hash(prev, ts, actor, action, case_id, detail)
        c.execute("INSERT INTO audit(ts,actor,action,case_id,detail,prev_hash,hash) VALUES(?,?,?,?,?,?,?)",
                  (ts, actor, action, case_id, detail, prev, h))

def audit_rows():
    with _c() as c:
        return [dict(r) for r in c.execute("SELECT * FROM audit ORDER BY id DESC")]

def verify_audit():
    """Returns (ok, first_bad_id). Any edit/deletion of an old row breaks the chain."""
    with _c() as c:
        rows = c.execute("SELECT * FROM audit ORDER BY id ASC").fetchall()
    prev = "GENESIS"
    for r in rows:
        if r["prev_hash"] != prev or r["hash"] != _hash(prev, r["ts"], r["actor"], r["action"], r["case_id"], r["detail"]):
            return False, r["id"]
        prev = r["hash"]
    return True, None

# ---------- consent ----------
def log_consent(actor, language, ttl_minutes):
    with _c() as c:
        cur = c.execute("INSERT INTO consent(ts,actor,language,ttl_minutes) VALUES(?,?,?,?)",
                        (time.time(), actor, language, ttl_minutes))
        cid = cur.lastrowid
    add_audit(actor, "CONSENT_GIVEN", "", f"consent_id={cid}, lang={language}, retention_min={ttl_minutes}")
    return cid

# ---------- cases ----------
def save_case(case_id, source, text_masked, case, assessment, ttl_minutes, voice_conf=None, consent_id=None):
    now = time.time()
    with _c() as c:
        c.execute("INSERT OR REPLACE INTO cases VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                  (case_id, now, now + ttl_minutes * 60, source, text_masked, json.dumps(case, ensure_ascii=False),
                   json.dumps(assessment, ensure_ascii=False), assessment["tag"], None, "New", voice_conf, consent_id))

def _row(r):
    d = dict(r)
    d["case"] = json.loads(d.pop("case_json"))
    d["assessment"] = json.loads(d.pop("assessment_json"))
    d["effective_tag"] = d["final_tag"] or d["tag"]
    return d

RANK = {"Urgent": 0, "Priority": 1, "Routine": 2}
def list_cases():
    with _c() as c:
        rows = [_row(r) for r in c.execute("SELECT * FROM cases")]
    # urgency first, then longest-waiting first; closed cases sink to the bottom
    rows.sort(key=lambda d: (d["status"] not in ("New", "Info requested"), RANK[d["effective_tag"]], d["created"]))
    return rows

def get_case(case_id):
    with _c() as c:
        r = c.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    return _row(r) if r else None

def set_status(case_id, status, final_tag=None):
    with _c() as c:
        if final_tag:
            c.execute("UPDATE cases SET status=?, final_tag=? WHERE id=?", (status, final_tag, case_id))
        else:
            c.execute("UPDATE cases SET status=? WHERE id=?", (status, case_id))

# ---------- messages between reviewer and health worker ----------
def add_message(case_id, actor, kind, text):
    with _c() as c:
        c.execute("INSERT INTO messages(case_id,ts,actor,kind,text) VALUES(?,?,?,?,?)",
                  (case_id, time.time(), actor, kind, text))

def get_messages(case_id):
    with _c() as c:
        return [dict(r) for r in c.execute("SELECT * FROM messages WHERE case_id=? ORDER BY id", (case_id,))]

def update_after_info(case_id, text_masked, case, assessment):
    """Health worker added info: refresh case, send it back to the queue.
    Escalate-only: if the system now rates the case higher than the reviewer's earlier tag, the old tag is dropped."""
    cur = get_case(case_id)
    final = cur["final_tag"]
    if final and RANK[assessment["tag"]] < RANK[final]:
        final = None
    with _c() as c:
        c.execute("UPDATE cases SET text_masked=?, case_json=?, assessment_json=?, tag=?, final_tag=?, status='New' WHERE id=?",
                  (text_masked, json.dumps(case, ensure_ascii=False), json.dumps(assessment, ensure_ascii=False),
                   assessment["tag"], final, case_id))

def purge_expired():
    """Auto-delete expired cases (data minimisation). Audit keeps only pseudonymous IDs."""
    with _c() as c:
        ids = [r["id"] for r in c.execute("SELECT id FROM cases WHERE expires < ?", (time.time(),))]
        c.execute("DELETE FROM cases WHERE expires < ?", (time.time(),))
        for i in ids:
            c.execute("DELETE FROM messages WHERE case_id=?", (i,))
    for i in ids:
        add_audit("system", "AUTO_DELETE", i, "retention period ended")
    return ids

def delete_case(case_id, actor):
    with _c() as c:
        c.execute("DELETE FROM cases WHERE id=?", (case_id,))
    add_audit(actor, "MANUAL_DELETE", case_id, "")

def reset_all():
    with _c() as c:
        c.executescript("DELETE FROM cases; DELETE FROM audit; DELETE FROM consent; DELETE FROM messages;")

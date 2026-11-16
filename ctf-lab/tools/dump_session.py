"""List CTF sessions or dump one session's lab_shell commands + result heads.
Usage: python dump_session.py list   |   python dump_session.py <index-from-end> """
import json, os, sqlite3, sys

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hermes-home", "state.db")
db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
db.row_factory = sqlite3.Row
sess = db.execute("select id, started_at, message_count, tool_call_count, title from sessions order by started_at").fetchall()

if sys.argv[1] == "list":
    for i, s in enumerate(sess):
        print(f"{i:2} {str(s['started_at'])[:19]}  msgs={s['message_count']:3} calls={s['tool_call_count']:3}  {s['title'] or ''}")
    sys.exit()

idx = int(sys.argv[1])
sid = sess[idx]["id"]
rows = db.execute("select role, content, tool_calls, reasoning_content from messages where session_id=? order by rowid", (sid,)).fetchall()
step = 0
for m in rows:
    if m["tool_calls"]:
        for c in json.loads(m["tool_calls"]):
            f = c.get("function", c)
            try:
                a = json.loads(f.get("arguments") or "{}")
            except Exception:
                a = {}
            step += 1
            if "lab_shell" in f.get("name", ""):
                print(f"\n[{step}] $ {a.get('command','')[:500]}")
            else:
                print(f"\n[{step}] {f.get('name','').split('__')[-1]}({json.dumps(a)[:150]})")
    elif m["role"] == "tool" and m["content"]:
        c = m["content"]
        i = c.find("untrusted data.")  # strip Hermes injection-guard preamble
        if i == -1:
            i = c.find("\n\n")
        body = (c[i + 15:] if i >= 0 else c).strip()
        n = int(os.environ.get("RESP", "300"))
        print(f"    -> {body[:n].strip()}")
    elif m["role"] == "assistant" and m["content"]:
        print(f"  (says) {m['content'][:300].strip()}")

import argparse, datetime as dt, json, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
J="worklog/CHANGELOG.jsonl"; M="worklog/CHANGELOG.md"
REQUIRED={"schema_version","entry_id","timestamp_utc","version","issue_id","summary","completed_items","code_files","evidence_paths","status","baseline_sha","author_role","correction_of"}
def parse(data):
    if not data.endswith(b"\n") or not data: raise ValueError("missing JSONL final newline")
    seen=set(); last=None
    for line in data.decode("utf-8").splitlines():
        x=json.loads(line)
        if set(x)!=REQUIRED or x["schema_version"]!="1.0": raise ValueError("schema mismatch")
        for k in ("entry_id","version","issue_id","summary","baseline_sha","author_role"):
            if not isinstance(x[k],str) or not x[k].strip(): raise ValueError("missing text: "+k)
        for k in ("completed_items","code_files","evidence_paths"):
            if not isinstance(x[k],list) or (k!="evidence_paths" and not x[k]): raise ValueError("invalid list "+k)
            if any(not isinstance(i,str) or not i.strip() for i in x[k]): raise ValueError("invalid list item")
        if x["status"] not in ("IMPLEMENTED","TESTED","BLOCKED","RELEASED","CORRECTION"): raise ValueError("status")
        if x["entry_id"] in seen: raise ValueError("duplicate entry")
        if x["status"]=="CORRECTION" and x["correction_of"] not in seen: raise ValueError("bad correction")
        now=dt.datetime.fromisoformat(x["timestamp_utc"].replace("Z","+00:00"))
        if now.utcoffset()!=dt.timedelta(0): raise ValueError("must be UTC")
        if last and now<last: raise ValueError("chronology")
        last=now;seen.add(x["entry_id"])
    return len(seen)
def verify(root=ROOT,base=None,read_base=None):
    j=(root/J).read_bytes();m=(root/M).read_bytes()
    n=parse(j)
    if not m.strip():raise ValueError("missing Markdown")
    for obj in (json.loads(s) for s in j.decode().splitlines()):
        if obj["entry_id"].encode() not in m:raise ValueError("Markdown missing entry "+obj["entry_id"])
    if base:
        if read_base is None:
            def read_base(p):
                r=subprocess.run(["git","show",base+":"+p],cwd=root,capture_output=True)
                if r.returncode:
                    # Bootstrap PR may have no history on main; only accept both absent.
                    if r.stderr and b"exists on disk" in r.stderr: return b""
                    raise ValueError("unable to read base "+p+": "+r.stderr.decode(errors="replace"))
                return r.stdout
        old_j=read_base(J);old_m=read_base(M)
        if not j.startswith(old_j) or not m.startswith(old_m): raise ValueError("historical log was rewritten")
        if old_j and n<=parse(old_j):raise ValueError("must append at least one record")
        if not old_j and n<1:raise ValueError("bootstrap record required")
        if len(m)<=len(old_m):raise ValueError("Markdown entry missing")
    return n
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--base");a=p.parse_args()
    try:print("WORKLOG PASS",verify(base=a.base))
    except Exception as e:print("WORKLOG BLOCKED",e);sys.exit(2)

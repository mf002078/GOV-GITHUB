import argparse, datetime as dt, hashlib, json, pathlib, re, subprocess, sys
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
def verify_legacy_fixture(root=ROOT,base=None,read_base=None):
    """Historical 1.0 fixture checks only; never a candidate admission API."""
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
LEGACY_ANCHOR = '1975ee74a62be815a032254d51603e15b4bbe093'
LOG_EXCEPTIONS = frozenset((J, M))
SHA = re.compile(r'^[0-9a-f]{40}$')
DIGEST = re.compile(r'^[0-9a-f]{64}$')


def git(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True)
    if result.returncode:
        raise ValueError('Git operation failed: ' + args[0])
    return result.stdout


def resolve(root, revision):
    # Never let a caller-controlled revision become a command option.
    if not isinstance(revision, str) or revision.startswith('-'):
        raise ValueError('invalid revision')
    return git(root, 'rev-parse', '--verify', '--end-of-options',
               revision + '^{commit}').decode().strip()


def blob(root, commit, path):
    return git(root, 'show', commit + ':' + path)


def safe_path(value):
    if (not isinstance(value, str) or not value or value.startswith('/')
            or '\\' in value or any(c in value for c in '\n\r\x00')
            or any(p in ('', '.', '..') for p in value.split('/'))):
        raise ValueError('invalid repository-relative path')
    return value


def render_entry(record):
    """Strict Markdown appendix; all fields mirrored, including arrays and nulls."""
    return ('\n## ' + record['entry_id'] + '\n\n```json\n'
            + json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2)
            + '\n```\n').encode('utf-8')


def strict_record(record, seen, last):
    if not isinstance(record, dict) or set(record) != REQUIRED or record['schema_version'] != '2.0':
        raise ValueError('new entries require exact schema 2.0')
    for key in ('entry_id', 'version', 'issue_id', 'summary', 'author_role'):
        if not isinstance(record[key], str) or not record[key].strip():
            raise ValueError('missing text: ' + key)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', record['entry_id']):
        raise ValueError('unsafe entry ID')
    if record['entry_id'] in seen:
        raise ValueError('duplicate entry ID')
    for key in ('completed_items', 'code_files', 'evidence_paths'):
        values = record[key]
        if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
            raise ValueError('invalid list: ' + key)
        if len(values) != len(set(values)):
            raise ValueError('duplicate list value: ' + key)
    if not record['completed_items'] or not record['evidence_paths']:
        raise ValueError('completed items and evidence references required')
    for p in record['code_files'] + record['evidence_paths']:
        safe_path(p)
    if not SHA.fullmatch(str(record['baseline_sha'])):
        raise ValueError('full parent SHA required')
    if record['status'] not in ('IMPLEMENTED', 'TESTED', 'BLOCKED', 'RELEASED', 'CORRECTION'):
        raise ValueError('invalid status')
    if record['status'] == 'CORRECTION':
        if not isinstance(record['correction_of'], str) or record['correction_of'] not in seen:
            raise ValueError('correction must reference a previous entry')
    elif record['correction_of'] is not None:
        raise ValueError('only CORRECTION may reference an old entry')
    if not isinstance(record['timestamp_utc'], str) or not re.fullmatch(
            r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z', record['timestamp_utc']):
        raise ValueError('explicit UTC timestamp required')
    now = dt.datetime.fromisoformat(record['timestamp_utc'].replace('Z', '+00:00'))
    if last is not None and now < last:
        raise ValueError('chronology')
    seen.add(record['entry_id'])
    return now


def validate_logs(journal, markdown, legacy_j, legacy_m):
    if not journal.startswith(legacy_j) or not markdown.startswith(legacy_m):
        raise ValueError('historical anchor bytes changed')
    seen = set()
    last = None
    for line in legacy_j.splitlines():
        old = json.loads(line)
        if 'entry_id' in old:
            seen.add(old['entry_id'])
            if old['entry_id'].encode() not in legacy_m:
                raise ValueError('legacy ID missing from Markdown')
        if 'timestamp_utc' in old:
            last = dt.datetime.fromisoformat(old['timestamp_utc'].replace('Z', '+00:00'))
    suffix = journal[len(legacy_j):]
    if suffix and not suffix.endswith(b'\n'):
        raise ValueError('JSONL final newline required')
    records = []
    for line in suffix.splitlines():
        record = json.loads(line)
        last = strict_record(record, seen, last)
        records.append(record)
    if markdown != legacy_m + b''.join(render_entry(r) for r in records):
        raise ValueError('JSONL/Markdown strict mirror mismatch')
    return records


def changed_paths(root, parent, commit):
    # Disable rename detection: a rename is explicitly old deletion + new addition.
    raw = git(root, 'diff', '--no-ext-diff', '--no-textconv', '--no-renames',
              '--name-only', '-z', parent, commit, '--')
    return {safe_path(p.decode('utf-8')) for p in raw.split(b'\x00') if p}


def verify_commits(root=ROOT, base=LEGACY_ANCHOR, head='HEAD', *, legacy_anchor=LEGACY_ANCHOR):
    """Inspect every commit, not just the aggregate diff. No network operations.

    legacy_anchor is a Python fixture seam; CLI cannot override the approved anchor.
    """
    anchor = resolve(root, legacy_anchor)
    base = resolve(root, base)
    head = resolve(root, head)
    if base != anchor:
        raise ValueError('base must equal approved legacy anchor; cannot skip revisions')
    for earlier, later in ((anchor, base), (base, head)):
        if git(root, 'merge-base', earlier, later).decode().strip() != earlier:
            raise ValueError('range must descend from approved anchor')
    legacy_j, legacy_m = (blob(root, anchor, p) for p in (J, M))
    before_j, before_m = (blob(root, base, p) for p in (J, M))
    before_records = validate_logs(before_j, before_m, legacy_j, legacy_m)
    commits = git(root, 'rev-list', '--reverse', '--first-parent', base + '..' + head).decode().splitlines()
    evidence_by_commit = {}
    for commit in commits:
        parents = git(root, 'rev-list', '--parents', '-n', '1', commit).decode().split()
        if len(parents) != 2:
            raise ValueError('merge commits require separately approved integration validation')
        parent = parents[1]
        journal, markdown = (blob(root, commit, p) for p in (J, M))
        if not journal.startswith(before_j) or not markdown.startswith(before_m):
            raise ValueError('historical log was rewritten')
        records = validate_logs(journal, markdown, legacy_j, legacy_m)
        new = records[len(before_records):]
        if not new or len(markdown) <= len(before_m):
            raise ValueError('every commit must append both logs')
        if any(r['baseline_sha'] != parent for r in new):
            raise ValueError('revision baseline must equal exact first parent')
        actual = changed_paths(root, parent, commit) - LOG_EXCEPTIONS
        listed = set()
        for rec in new:
            listed.update(rec['code_files'])
        if listed != actual:
            raise ValueError('code_files differs from actual commit paths: missing='
                             + repr(sorted(actual-listed)) + ' extra=' + repr(sorted(listed-actual)))
        evidence_by_commit[commit] = sorted({p for r in new for p in r['evidence_paths']})
        before_j, before_m, before_records = journal, markdown, records
    return dict(candidate_sha=head, commits=len(commits), entries=len(before_records),
                legacy='LEGACY_COMPAT', provenance='NOT_ATTESTED',
                evidence_by_commit=evidence_by_commit)


def verify_evidence(root, candidate_sha, evidence, expected_paths):
    fields = {'schema_version', 'candidate_sha', 'provenance', 'source_mode', 'artifacts'}
    if not isinstance(evidence, dict) or set(evidence) != fields:
        raise ValueError('invalid evidence fields')
    if (not SHA.fullmatch(str(candidate_sha)) or evidence['candidate_sha'] != candidate_sha
            or evidence['schema_version'] != '1.0' or evidence['source_mode'] != 'synthetic'
            or evidence['provenance'] != 'NOT_ATTESTED'):
        raise ValueError('evidence SHA/mode/provenance mismatch')
    if not isinstance(evidence['artifacts'], list) or not evidence['artifacts']:
        raise ValueError('evidence artifacts required')
    paths = set()
    for artifact in evidence['artifacts']:
        if not isinstance(artifact, dict) or set(artifact) != {'path', 'sha256'}:
            raise ValueError('invalid artifact fields')
        path = safe_path(artifact['path'])
        if path in paths or not DIGEST.fullmatch(str(artifact['sha256'])):
            raise ValueError('duplicate artifact or invalid SHA256')
        if hashlib.sha256(blob(root, candidate_sha, path)).hexdigest() != artifact['sha256']:
            raise ValueError('artifact digest mismatch')
        paths.add(path)
    if paths != set(expected_paths):
        raise ValueError('evidence paths do not match revision references')
    return 'NOT_ATTESTED'


def verify_manifest(root, result, records):
    """Validate the complete revision set; shared by CLI and candidate transport."""
    if not isinstance(records, list):
        raise ValueError('evidence manifest must be an array')
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError('invalid evidence record')
        sha = record.get('candidate_sha')
        if not isinstance(sha, str) or sha in seen or sha not in result['evidence_by_commit']:
            raise ValueError('duplicate or unexpected candidate SHA')
        verify_evidence(root, sha, record, result['evidence_by_commit'][sha])
        seen.add(sha)
    if seen != set(result['evidence_by_commit']):
        raise ValueError('every candidate commit requires evidence')


def main():
    parser = argparse.ArgumentParser(description='Offline candidate checker; not a Protected Validator')
    parser.add_argument('--base', default=LEGACY_ANCHOR)
    parser.add_argument('--head', default='HEAD')
    parser.add_argument('--evidence', type=pathlib.Path,
                        help='post-commit external JSON array: one evidence record per revision')
    args = parser.parse_args()
    try:
        result = verify_commits(base=args.base, head=args.head)
        # Do not silently validate a committed snapshot while edits are pending.
        if git(ROOT, 'status', '--porcelain', '--untracked-files=all').strip():
            raise ValueError('working tree must be clean; committed snapshot only')
        if not args.evidence and result['commits']:
            raise ValueError('external evidence manifest required for candidate commits')
        if args.evidence:
            records = json.loads(args.evidence.read_text(encoding='utf-8'))
            verify_manifest(ROOT, result, records)
        print('L1 STRUCTURE PASS', json.dumps(result, sort_keys=True))
        print('Gate A BLOCKED/UNVERIFIED; NOT_ATTESTED; candidate-controlled checks only')
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print('WORKLOG BLOCKED', exc)
        return 2


if __name__ == '__main__':
    sys.exit(main())

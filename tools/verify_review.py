"""Offline advisory-review contract validator; not a protected Gate A."""
import argparse
import json
import re
import sys
from pathlib import Path

SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
STATUSES = {"ADVISORY_PASS", "REQUEST_CHANGES", "INSUFFICIENT_EVIDENCE"}
FIELDS = {"schema_version", "repository", "pr_number", "head_sha", "issue_id", "review_status", "findings", "evidence", "policy_version"}

def validate(record, *, expected_repo, expected_pr, expected_sha):
    if not isinstance(record, dict) or set(record) != FIELDS:
        raise ValueError("schema mismatch")
    if record["schema_version"] != "1.0":
        raise ValueError("invalid schema version")
    if record["repository"] != expected_repo or record["pr_number"] != expected_pr:
        raise ValueError("incorrect repository or PR")
    if not GIT_SHA.fullmatch(str(expected_sha)) or record["head_sha"] != expected_sha:
        raise ValueError("stale or invalid commit SHA")
    if not isinstance(record["issue_id"], str) or not record["issue_id"].strip():
        raise ValueError("missing issue")
    if record["review_status"] not in STATUSES:
        raise ValueError("unrecognized advisory status")
    if not isinstance(record["policy_version"], str) or not record["policy_version"].strip():
        raise ValueError("policy version missing")
    if not isinstance(record["findings"], list) or not isinstance(record["evidence"], list):
        raise ValueError("invalid findings or evidence")
    if record["review_status"] == "ADVISORY_PASS" and not record["evidence"]:
        raise ValueError("pass requires evidence")
    for finding in record["findings"]:
        if not isinstance(finding, dict) or set(finding) != {"severity", "message"}:
            raise ValueError("invalid finding")
        if finding["severity"] not in {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            raise ValueError("invalid severity")
        if not isinstance(finding["message"], str) or not finding["message"].strip():
            raise ValueError("empty finding")
    for item in record["evidence"]:
        if not isinstance(item, dict) or set(item) != {"name", "sha256"}:
            raise ValueError("invalid evidence")
        if not isinstance(item["name"], str) or not item["name"].strip() or not SHA256.fullmatch(str(item["sha256"])):
            raise ValueError("invalid evidence digest")
    if record["review_status"] == "ADVISORY_PASS" and any(x["severity"] in {"HIGH", "CRITICAL"} for x in record["findings"]):
        raise ValueError("pass cannot contain severe finding")
    return "ADVISORY_RECORD_WELL_FORMED_NOT_ACCEPTED"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("path",type=Path)
    p.add_argument("--repo",required=True)
    p.add_argument("--pr",type=int,required=True)
    p.add_argument("--sha",required=True)
    args=p.parse_args()
    try:
        result=validate(json.loads(args.path.read_text(encoding="utf-8")),expected_repo=args.repo,expected_pr=args.pr,expected_sha=args.sha)
        print(result)
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print("BLOCKED:",e)
        return 2

if __name__=="__main__":sys.exit(main())

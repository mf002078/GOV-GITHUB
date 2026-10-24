# Continuous Engineering Work Log
Append only — never delete or edit history.
## GOV-BOOTSTRAP-001 — v0.2.1-pilot
- Time (UTC): 2026-10-24T11:00:00Z
- Issue: GOV-GITHUB-001
- Completed: Append-only logs, PR checks, synthetic MD03 pilot
- Summary: Initial GitHub governance PR pilot; cloud CI pending.
- Source: AGENTS.md; tools/check_worklog.py; tests/test_check_worklog.py; .github/workflows/governance.yml
- Evidence: pending
- Status: IMPLEMENTED
- Baseline: d97a686d139f5635378e4d73d680a2fbbcb552f4

## GOV-PROTECTION-002 — v0.2.2-pilot
- Time (UTC): 2026-10-24T12:03:23Z
- Issue: GOV-GITHUB-001
- Completed: protected rollout checklist; independent review and negative test requirements
- Summary: documented required GitHub controls; ruleset not yet applied
- Source: docs/PROTECTED_ROLLOUT.md
- Evidence: https://github.com/mf002078/GOV-GITHUB/actions/runs/40091706722
- Status: IMPLEMENTED
- Baseline: d97a686d139f5635378e4d73d680a2fbbcb552f4

## GOV-GITHUB-002-REV-001

```json
{
  "author_role": "Codex",
  "baseline_sha": "1975ee74a62be815a032254d51603e15b4bbe093",
  "code_files": [
    "tools/check_worklog.py",
    "tests/test_check_worklog.py",
    "tests/test_revision_contract.py"
  ],
  "completed_items": [
    "R01 per-commit path comparison; rename as delete/add; binary paths; fixed two-log exception",
    "R02 schema 2.0 canonical Markdown mirror; legacy prefix compatibility",
    "R03 exact candidate and blob SHA256 structural checks only; NOT_ATTESTED",
    "R04 test-first red: 27 tests, 33 errors before implementation; green: 32 tests passed",
    "R05 immutable per-parent log prefixes and append-only corrections"
  ],
  "correction_of": null,
  "entry_id": "GOV-GITHUB-002-REV-001",
  "evidence_paths": [
    "tests/test_revision_contract.py",
    "tests/test_check_worklog.py"
  ],
  "issue_id": "GOV-GITHUB-002",
  "schema_version": "2.0",
  "status": "TESTED",
  "summary": "Implement first-parent diff, strict new-entry mirrors and post-commit NOT_ATTESTED evidence validation; initial 32 synthetic tests pass.",
  "timestamp_utc": "2026-10-24T15:50:07.714402Z",
  "version": "0.3.0-candidate.1"
}
```

## GOV-GITHUB-002-REV-002

```json
{
  "author_role": "Codex",
  "baseline_sha": "1975ee74a62be815a032254d51603e15b4bbe093",
  "code_files": [
    "tools/check_worklog.py",
    "tests/test_revision_contract.py",
    "docs/GOV_GITHUB_002_CONTRACT.md",
    "docs/evidence/GOV-GITHUB-002-tests.json"
  ],
  "completed_items": [
    "Reject alternate base that skips a bad intermediate commit; reject merges",
    "Additional deletion, multi-commit, symlink-no-follow, URL/source-mode/evidence field tests",
    "Document exact path and mirror contracts, evidence transport, residual D05/Gate A controls",
    "Capture actual Python unittest output: 42 tests, exit 0; no failed/skipped tests",
    "Existing CI remains fail-closed without external manifest; no workflow or formal policy changes"
  ],
  "correction_of": null,
  "entry_id": "GOV-GITHUB-002-REV-002",
  "evidence_paths": [
    "docs/evidence/GOV-GITHUB-002-tests.json",
    "docs/GOV_GITHUB_002_CONTRACT.md"
  ],
  "issue_id": "GOV-GITHUB-002",
  "schema_version": "2.0",
  "status": "TESTED",
  "summary": "Close base-range skipping; document owner-scoped Gate D and dual contract; 42 offline tests pass with full captured output.",
  "timestamp_utc": "2026-10-24T15:51:53.992901Z",
  "version": "0.3.0-candidate.2"
}
```

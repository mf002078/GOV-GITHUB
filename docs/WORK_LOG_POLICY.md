# WORK-LOG-001 — Append-Only Engineering Log (PROPOSED)
The approved YMC-GOV-001 v1.0.0 remains unchanged.
Codex and LLM MUST append one record after each revision to both worklog/CHANGELOG.jsonl and worklog/CHANGELOG.md.
Fields: schema_version, entry_id, timestamp_utc, version, issue_id, summary, completed_items, code_files, evidence_paths, status, baseline_sha, author_role, correction_of.
Previously committed bytes MUST remain identical; use a new CORRECTION entry to fix mistakes.
PR CI compares both logs to the exact PR base Git commit. A pass is only a check against that Git basis, NOT tamper-proof storage or independent Gate A acceptance.
Changes to CI, policy, checker and reviewer configuration require independent scrutiny; candidate-controlled CI cannot self-approve.

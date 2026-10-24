# Mandatory LLM and Codex rules

1. Respect approved project policy and the current Issue/Gate D scope.
2. For every revision append version, UTC timestamp, accomplishments, summary, code file paths, evidence and status to BOTH `worklog/CHANGELOG.jsonl` and `worklog/CHANGELOG.md`. Never delete, edit, reorder, shorten, or rewrite historical entries; corrections require a NEW correction entry.
3. AI-generated reviews are advisory. Never claim an LLM response constitutes a second GitHub account's approval, nor bypass a protected branch ruleset.
4. Require exact commit SHA, independently executed tests and verified evidence before Gate A. Treat evidence provided by candidate branch as untrusted until attested by trusted runner.
5. No broker credentials, account/order operations, live quotes, private logs, or production deployment in this repository.

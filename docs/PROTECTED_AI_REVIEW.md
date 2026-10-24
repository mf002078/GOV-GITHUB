# GOV-AI-REVIEW-001 — reusable protected reviewer blueprint
Status: IMPLEMENTATION PROTOTYPE / NOT AN INDEPENDENT PROTECTED SERVICE.

## Separation of responsibility
- **Codex developer**: candidate worktree, source changes and unit tests; no protected credentials.
- **AI reviewer**: read-only static context (PR diff, specification, hashes), structured advisory findings; no GitHub approval rights.
- **Trusted CI/validator**: runs out-of-band from a separately protected repository or independently managed runner, verifies exact candidate commit, runs owned negative tests, produces signed attestations/status under a dedicated identity.
- **GitHub reviewer**: independent user with Write access supplies one formal approval as currently required by GOV-MAIN-PROTECTION. Do not disable this rule. A bot's ordinary comment or check-run is not a GitHub approving review.
- **Owner**: resolves policy, protected permissions, and deployment decisions.

## Deploy in stages
1. Keep existing PR #2 unmerged until independent reviewer is available. This PR can test review *infrastructure* only.
2. Use the offline validator in tools/verify_review.py against synthetic fixtures, including stale SHA, mismatch, missing evidence, and untrusted actor tests.
3. Put protected reviewer workflow/source and policy snapshot in a **separate, independently administered repository**, with protected branch and CODEOWNERS. Candidate PR may not change it.
4. Use GitHub App installation or separate authorized service identity with narrowly scoped permissions for read-only source and check-run publication. Do NOT store its private key in PR-accessible jobs.
5. Take the PR head SHA from trusted GitHub event metadata; retrieve immutable code at that SHA. Verify test attestations were created at that same SHA; no arbitrary URLs, shell or instructions from PR description.
6. Call a supported model with a JSON Schema contract via the API, within a sandbox that has **no write privileges**. Require evidence, reproducibility and clear unknowns. Model judgment stays ADVISORY.
7. Protected independent CI publishes unique required status, e.g. `protected-review / validate`, after positive and negative exercises. Add it to Ruleset only once reliable.
8. Never run untrusted PR source under privileged `pull_request_target` or under secrets-bearing jobs. Use an unprivileged PR build and privileged follow-up only on data, without executing candidate artifacts.
9. Retain independent human approval for now. If the owner later elects an automated merge regime, that would require a distinct formal governance amendment and an explicit authorized rule change, not AI simulation of an account.

## Evidence contract
A candidate report is **not** a protected attestation. Example fields:
`schema_version, repository, pr_number, head_sha, issue_id, review_status, findings, evidence, policy_version`.
`review_status` can only be `ADVISORY_PASS`, `REQUEST_CHANGES`, or `INSUFFICIENT_EVIDENCE`.
Each evidence item binds a logical name and SHA256 of material already collected. The offline checker does not fetch material from untrusted URLs.
Protected service, when deployed, must separately verify artifact digests, identity, signature and test results; these are NOT established by this prototype.

## Acceptance matrix
L0 offline schema + negative tests only; L1 PR check-run from candidate job; L2 protected CI service identity with denied token access from candidate; L3 policy owner and independent reviewer, review/stale approval; L4–L5 Windows MC/vendor test evidence remains entirely separate.
Never relabel an L0/L1 result as L2/L3.

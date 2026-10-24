# Protected GitHub PR rollout — operator checklist
Status: **NOT CONFIGURED / DO NOT MERGE**. This document records recommended settings; it does not apply them.

## Configure on github.com
1. Open repository Settings → Rules → Rulesets → New branch ruleset; target default branch `main`; set **Active**.
2. Require a pull request before merging, at least **1 approval from an independent account**, dismiss stale approvals on new commits, and require approval of the most recent reviewable push where available.
3. Require passing check **`validate`** from **Governance history checks** (select the check produced by a genuine PR run). Require branches be up to date when sensible. Require conversation resolution.
4. Prevent force pushes and branch deletion; restrict bypass access and direct updates to `main`. Review actual account plan/repository entitlement if controls are not available.
5. Protect changes to `.github/workflows/**`, `tools/check_worklog.py`, `docs/WORK_LOG_POLICY.md`, `AGENTS.md`, `.github/CODEOWNERS`, and policy documents with separate accountable reviewers. CODEOWNERS rules without branch protection are advisory.
6. Use a separate trusted CI/review identity and approved policy source for real Gate A. Running the checker from the candidate PR does not establish independent enforcement.
7. Keep PR #2 as **Draft** until controls verified, positive/negative tests recorded, and a genuinely independent reviewer approved; only then consider merge.

## Verification exercises (must retain links/evidence)
- Valid append-only entry => CI pass.
- Edit any pre-existing JSONL/Markdown byte => required CI fail.
- Change workflow/checker without protected reviewer => merge blocked.
- Attempt direct main push/force push => denied to developer identity.
- Re-review after change to PR => old approval stale.
- All evidence must refer to the exact commit SHA; check failure cannot be bypassed by a candidate-modified workflow.

## Current state
- Repo: mf002078/GOV-GITHUB; PR #2.
- GitHub Actions initial run: 40091706722 (successful).
- GitHub ruleset: **not verified**, branch restrictions: **not verified**.
- Independent reviewer: **not established**. An LLM review comment made via the owner's integration is NOT an independent identity.
- YMC-GOV-001 is approved policy; WORK-LOG-001 is a proposal until separately approved.
- MD03-ATOMIC-001 real implementation and MC/live acceptance: **not tested**.

## Template portability
Place generic enforcement rules in the reusable core. Put broker-specific restrictions in YuantaMC profile, never contaminate generic profiles with real credentials or endpoints. Verify on an independent second repository before tagging v1.0.

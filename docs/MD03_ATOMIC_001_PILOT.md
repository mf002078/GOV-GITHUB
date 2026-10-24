# MD03-ATOMIC-001 — Acceptance contract
Pilot Issue: #1. This PR does not implement actual YuantaMC Raw Journal atomicity.
Future evidence requires fault injection before/during/after transaction commit, raw-projection recoverability, no duplicate logical event on replay, and RAW19 plus ReqType preservation.
Do not claim a production MD-03 PASS without actual source tests and independent Gate A review.
No live broker, MultiCharts, account/order or credentials are in scope.

import copy
import unittest
from tools.verify_review import validate

SHA="a"*40
R={"schema_version":"1.0","repository":"mf002078/GOV-GITHUB","pr_number":4,"head_sha":SHA,"issue_id":"GOV-AI-REVIEW-001","review_status":"ADVISORY_PASS","findings":[],"evidence":[{"name":"ci-result","sha256":"b"*64}],"policy_version":"YMC-GOV-001-v1.0.0"}

class ReviewContractTests(unittest.TestCase):
 def ok(self,x):
  return validate(x,expected_repo="mf002078/GOV-GITHUB",expected_pr=4,expected_sha=SHA)
 def test_advisory(self):self.assertEqual("ADVISORY_RECORD_WELL_FORMED_NOT_ACCEPTED",self.ok(R))
 def test_stale_sha(self):
  x=dict(R,head_sha="c"*40)
  with self.assertRaises(ValueError):self.ok(x)
 def test_wrong_repo(self):
  with self.assertRaises(ValueError):self.ok(dict(R,repository="other/repo"))
 def test_wrong_pr(self):
  with self.assertRaises(ValueError):self.ok(dict(R,pr_number=9))
 def test_no_evidence(self):
  with self.assertRaises(ValueError):self.ok(dict(R,evidence=[]))
 def test_high_finding(self):
  x=dict(R,findings=[{"severity":"HIGH","message":"risk"}])
  with self.assertRaises(ValueError):self.ok(x)
 def test_no_merge_authority(self):
  with self.assertRaises(ValueError):self.ok(dict(R,review_status="APPROVED"))
 def test_bad_digest(self):
  with self.assertRaises(ValueError):self.ok(dict(R,evidence=[{"name":"ci-result","sha256":"xyz"}]))
 def test_missing_fields(self):
  x=dict(R);x.pop("policy_version")
  with self.assertRaises(ValueError):self.ok(x)

if __name__=="__main__":unittest.main()

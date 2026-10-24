import json,pathlib,tempfile,unittest
from tools.check_worklog import verify_legacy_fixture as verify
REC={"schema_version":"1.0","entry_id":"A","timestamp_utc":"2026-10-24T11:00:00Z","version":"1","issue_id":"X","summary":"change","completed_items":["done"],"code_files":["a.py"],"evidence_paths":[],"status":"TESTED","baseline_sha":"base","author_role":"Codex","correction_of":None}
class HistoryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.r=pathlib.Path(self.tmp.name);(self.r/"worklog").mkdir()
  self.j=(json.dumps(REC)+"\n").encode();self.m=b"# Log\nA\n"
  (self.r/"worklog/CHANGELOG.jsonl").write_bytes(self.j);(self.r/"worklog/CHANGELOG.md").write_bytes(self.m)
 def tearDown(self):self.tmp.cleanup()
 def old(self,p):return self.j if p.endswith("jsonl") else self.m
 def append(self):
  b=dict(REC,entry_id="B",timestamp_utc="2026-10-24T12:00:00Z")
  (self.r/"worklog/CHANGELOG.jsonl").write_bytes(self.j+(json.dumps(b)+"\n").encode())
  (self.r/"worklog/CHANGELOG.md").write_bytes(self.m+b"B\n")
 def test_append(self):self.append();self.assertEqual(2,verify(self.r,"base",self.old))
 def test_no_append(self):
  with self.assertRaises(ValueError):verify(self.r,"base",self.old)
 def test_mutation(self):
  self.append();p=self.r/"worklog/CHANGELOG.jsonl";p.write_bytes(p.read_bytes().replace(b'"summary": "change"',b'"summary": "altered"',1))
  with self.assertRaises(ValueError):verify(self.r,"base",self.old)
 def test_markdown_removal(self):
  self.append();(self.r/"worklog/CHANGELOG.md").write_bytes(b"# replaced\nB\n")
  with self.assertRaises(ValueError):verify(self.r,"base",self.old)
 def test_missing_field(self):
  v=dict(REC);v.pop("version");(self.r/"worklog/CHANGELOG.jsonl").write_text(json.dumps(v)+"\n")
  with self.assertRaises(ValueError):verify(self.r)
if __name__=="__main__":unittest.main()

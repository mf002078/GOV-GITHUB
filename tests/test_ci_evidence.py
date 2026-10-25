"""Candidate CI transport tests: local synthetic Git objects, no network."""
import json
import pathlib
import tempfile
import unittest

import test_revision_contract as fixture
from tools import check_worklog as check
from tools import prepare_ci_evidence as transport


class EvidenceTransportTests(unittest.TestCase):
    setUp = fixture.RevisionContractTests.setUp
    git = fixture.RevisionContractTests.git
    write = fixture.RevisionContractTests.write
    revision = fixture.RevisionContractTests.revision

    def prepare(self, expected=None, base=None):
        return transport.prepare_manifest(
            self.root, expected or self.git('rev-parse', 'HEAD'),
            base or self.anchor, legacy_anchor=self.anchor)

    def test_exact_head_and_legacy_base(self):
        self.revision()
        result, records = self.prepare()
        self.assertEqual(self.git('rev-parse', 'HEAD'), result['candidate_sha'])
        self.assertEqual('NOT_ATTESTED', records[0]['provenance'])
        check.verify_manifest(self.root, result, records)

    def test_all_commits_get_individual_evidence(self):
        self.revision(); first = self.git('rev-parse', 'HEAD')
        self.revision({'src/a.py': b'next'})
        result, records = self.prepare(base=first)
        self.assertEqual(2, len(records))
        self.assertEqual(first, records[0]['candidate_sha'])
        check.verify_manifest(self.root, result, records)

    def test_missing_manifest(self):
        self.revision(); result, _ = self.prepare()
        with self.assertRaises(ValueError): check.verify_manifest(self.root, result, None)

    def test_empty_manifest(self):
        self.revision(); result, _ = self.prepare()
        with self.assertRaises(ValueError): check.verify_manifest(self.root, result, [])

    def test_missing_revision_manifest(self):
        self.revision(); self.revision({'src/a.py': b'next'})
        result, records = self.prepare()
        with self.assertRaises(ValueError): check.verify_manifest(self.root, result, records[:1])

    def test_duplicate_revision_manifest(self):
        self.revision(); result, records = self.prepare()
        with self.assertRaises(ValueError): check.verify_manifest(self.root, result, records*2)

    def test_stale_manifest_sha(self):
        self.revision(); result, records = self.prepare()
        records[0]['candidate_sha'] = self.anchor
        with self.assertRaises(ValueError): check.verify_manifest(self.root, result, records)

    def test_expected_head_mismatch(self):
        self.revision()
        with self.assertRaises(ValueError): self.prepare(expected=self.anchor)

    def test_expected_sha_is_not_ref_or_expression(self):
        self.revision()
        for value in ['HEAD', '--help', 'a'*39, '${{ bad }}']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.prepare(expected=value)

    def test_forged_provenance(self):
        self.revision(); result, records = self.prepare()
        records[0]['provenance'] = 'ATTESTED'
        with self.assertRaises(ValueError): check.verify_manifest(self.root, result, records)

    def test_unknown_origin_field_rejected(self):
        self.revision(); result, records = self.prepare()
        records[0]['trusted_runner'] = 'self-asserted'
        with self.assertRaises(ValueError): check.verify_manifest(self.root, result, records)

    def test_tampered_sha256(self):
        self.revision(); result, records = self.prepare()
        records[0]['artifacts'][0]['sha256'] = '0'*64
        with self.assertRaises(ValueError): check.verify_manifest(self.root, result, records)

    def test_dirty_checkout_rejected(self):
        self.revision(); self.write('src/a.py', b'edited')
        with self.assertRaises(ValueError): self.prepare()

    def test_untracked_checkout_rejected(self):
        self.revision(); self.write('untracked.txt', b'x')
        with self.assertRaises(ValueError): self.prepare()

    def test_pr_base_cannot_be_unrelated_or_ahead(self):
        self.revision(); candidate = self.git('rev-parse', 'HEAD')
        self.revision({'src/a.py': b'next'}); ahead = self.git('rev-parse','HEAD')
        self.git('checkout', '-q', candidate)
        with self.assertRaises(ValueError): self.prepare(base=ahead)

    def test_old_unqualified_pr_base_rejected(self):
        self.revision()
        # Empty tree/object is not a qualified baseline commit.
        with self.assertRaises(ValueError): self.prepare(base='0'*40)

    def test_preserves_history_failure(self):
        self.revision(); self.write(check.M, b'rewritten')
        self.git('add','.'); self.git('commit','-qm','bad history')
        with self.assertRaises(ValueError): self.prepare()

    def test_output_inside_checkout_rejected(self):
        self.revision()
        with self.assertRaises(ValueError):
            transport.write_manifest(self.root, self.root/'manifest.json', [])

    def test_manifest_roundtrip_external_file(self):
        self.revision(); result, records = self.prepare()
        with tempfile.TemporaryDirectory() as directory:
            output=pathlib.Path(directory)/'manifest.json'
            transport.write_manifest(self.root, output, records)
            check.verify_manifest(self.root, result, json.loads(output.read_text()))

    def test_stale_output_not_overwritten(self):
        self.revision(); _, records = self.prepare()
        with tempfile.TemporaryDirectory() as directory:
            output=pathlib.Path(directory)/'manifest.json'
            output.write_text('stale synthetic content')
            with self.assertRaises(FileExistsError):
                transport.write_manifest(self.root, output, records)
            self.assertEqual('stale synthetic content', output.read_text())

    def test_unknown_artifact_field_rejected(self):
        self.revision(); result, records = self.prepare()
        records[0]['artifacts'][0]['trusted'] = True
        with self.assertRaises(ValueError): check.verify_manifest(self.root, result, records)

    def test_github_merge_snapshot_is_not_pr_head(self):
        self.revision(); head=self.git('rev-parse','HEAD')
        self.git('checkout','-qb','merge-snapshot')
        self.git('merge','--no-ff','--no-edit',self.anchor)
        # Create a synthetic extra commit, like a non-head CI checkout.
        self.write('merge-only',b'x'); self.git('add','.'); self.git('commit','-qm','snapshot')
        with self.assertRaises(ValueError): self.prepare(expected=head)

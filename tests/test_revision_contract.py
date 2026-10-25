"""Synthetic Git repositories only; no remote or protected-resource operations."""
import hashlib
import json
import pathlib
import subprocess
import tempfile
import unittest

from tools import check_worklog as check


class RevisionContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Synthetic')
        self.git('config', 'user.email', 'synthetic@example.invalid')
        self.write(check.J, b'{"legacy":true}\n')
        self.write(check.M, b'# historical bytes\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'synthetic anchor')
        self.anchor = self.git('rev-parse', 'HEAD')
        # Synthetic anchors are explicit test arguments, never CLI policy overrides.

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args]).decode().strip()

    def write(self, path, data):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def revision(self, files=None, record_changes=None, markdown_changes=None):
        files = {'src/a.py': b'example\n'} if files is None else files
        parent = self.git('rev-parse', 'HEAD')
        for p, data in files.items():
            self.write(p, data)
        changes = self.git('diff', '--name-only', 'HEAD').splitlines()
        untracked = self.git('ls-files', '--others', '--exclude-standard').splitlines()
        paths = sorted(set(changes + untracked) - set(check.LOG_EXCEPTIONS))
        n = len(self.git('rev-list', 'HEAD').splitlines())
        rec = dict(schema_version='2.0', entry_id=f'REV-{n}',
                   timestamp_utc=f'2026-10-24T16:00:{n:02d}Z', version=f'0.{n}',
                   issue_id='GOV-GITHUB-002', summary='Synthetic revision',
                   completed_items=['Synthetic implementation'], code_files=paths,
                   evidence_paths=paths[:1], status='TESTED', baseline_sha=parent,
                   author_role='Codex', correction_of=None)
        rec.update(record_changes or {})
        with (self.root / check.J).open('ab') as f:
            f.write((json.dumps(rec, ensure_ascii=False) + '\n').encode())
        mirror = dict(rec, **(markdown_changes or {}))
        with (self.root / check.M).open('ab') as f:
            f.write(check.render_entry(mirror))
        self.git('add', '-A')
        self.git('commit', '-qm', 'synthetic revision')
        return rec

    def verify(self):
        return check.verify_commits(self.root, self.anchor, 'HEAD', legacy_anchor=self.anchor)

    def evidence(self):
        head = self.git('rev-parse', 'HEAD')
        return dict(schema_version='1.0', candidate_sha=head, provenance='NOT_ATTESTED',
                    source_mode='synthetic', artifacts=[dict(path='src/a.py',
                    sha256=hashlib.sha256((self.root/'src/a.py').read_bytes()).hexdigest())])

    def test_valid_append(self):
        self.revision()
        self.assertEqual(1, self.verify()['commits'])

    def test_missing_changed_path(self):
        self.revision(record_changes={'code_files': []})
        with self.assertRaises(ValueError): self.verify()

    def test_mislisted_path(self):
        self.revision(record_changes={'code_files': ['unrelated.py']})
        with self.assertRaises(ValueError): self.verify()

    def test_no_log_append(self):
        self.write('src/a.py', b'x')
        self.git('add', '.'); self.git('commit', '-qm', 'missing log')
        with self.assertRaises(ValueError): self.verify()

    def test_unapproved_exception(self):
        self.revision({'.github/workflows/new.yml': b'changed\n'}, {'code_files': []})
        with self.assertRaises(ValueError): self.verify()

    def test_mirror_fields(self):
        for field, value in [('summary', 'wrong'), ('version', 'wrong'),
                             ('timestamp_utc', '2026-10-24T00:00:00Z'),
                             ('completed_items', ['wrong']), ('status', 'BLOCKED')]:
            with self.subTest(field=field):
                parent = self.git('rev-parse', 'HEAD')
                self.revision(markdown_changes={field: value})
                with self.assertRaises(ValueError): self.verify()
                self.git('reset', '--hard', parent)

    def test_history_mutation_truncation_reorder(self):
        for data in [b'changed\n', b'', b'\n{"legacy":true}\n']:
            with self.subTest(data=data):
                self.git('reset', '--hard', self.anchor)
                self.revision()
                self.write(check.J, data)
                self.git('add', '.'); self.git('commit', '-qm', 'bad history')
                with self.assertRaises(ValueError): self.verify()

    def test_markdown_history_rewrite(self):
        self.revision()
        self.write(check.M, b'replacement\n')
        self.git('add', '.'); self.git('commit', '-qm', 'rewrite')
        with self.assertRaises(ValueError): self.verify()

    def test_invalid_correction(self):
        self.revision(record_changes={'status': 'CORRECTION', 'correction_of': 'UNKNOWN'})
        with self.assertRaises(ValueError): self.verify()

    def test_correction_requires_correction_status(self):
        self.revision(record_changes={'correction_of': 'ANY'})
        with self.assertRaises(ValueError): self.verify()

    def test_valid_correction(self):
        self.revision()
        self.revision({'src/a.py': b'corrected\n'},
                      {'status': 'CORRECTION', 'correction_of': 'REV-1'})
        self.assertEqual(2, self.verify()['commits'])

    def test_duplicate_entry(self):
        self.revision()
        self.revision({'src/a.py': b'v2'}, {'entry_id': 'REV-1'})
        with self.assertRaises(ValueError): self.verify()

    def test_non_utc(self):
        self.revision(record_changes={'timestamp_utc': '2026-10-24T16:00:00+08:00'})
        with self.assertRaises(ValueError): self.verify()

    def test_legacy_schema_cannot_be_appended(self):
        self.revision(record_changes={'schema_version': '1.0'})
        with self.assertRaises(ValueError): self.verify()

    def test_binary(self):
        self.revision({'assets/data.bin': b'\x00\xff\x01'})
        self.assertEqual(1, self.verify()['commits'])

    def test_rename_both_paths(self):
        self.revision()
        self.git('mv', 'src/a.py', 'src/renamed.py')
        self.revision({}, {'code_files': ['src/a.py', 'src/renamed.py'],
                           'evidence_paths': ['src/renamed.py']})
        self.assertEqual(2, self.verify()['commits'])

    def test_rename_missing_old_path(self):
        self.revision()
        self.git('mv', 'src/a.py', 'src/renamed.py')
        self.revision({}, {'code_files': ['src/renamed.py'],
                           'evidence_paths': ['src/renamed.py']})
        with self.assertRaises(ValueError): self.verify()

    def test_multiple_commits_cannot_hide_omission(self):
        self.revision()
        self.write('src/unlogged.py', b'bad')
        self.git('add', '.'); self.git('commit', '-qm', 'unlogged middle commit')
        self.revision({'src/a.py': b'v3'})
        with self.assertRaises(ValueError): self.verify()

    def test_log_only_correction(self):
        self.revision()
        self.revision({}, {'code_files': [], 'status': 'CORRECTION',
                           'correction_of': 'REV-1', 'evidence_paths': ['src/a.py']})
        self.assertEqual(2, self.verify()['commits'])

    def test_expected_candidate_sha(self):
        self.revision(); ev = self.evidence(); ev['candidate_sha'] = '0'*40
        with self.assertRaises(ValueError):
            check.verify_evidence(self.root, self.git('rev-parse','HEAD'), ev, ['src/a.py'])

    def test_valid_evidence_not_attested(self):
        self.revision()
        self.assertEqual('NOT_ATTESTED', check.verify_evidence(
            self.root, self.git('rev-parse','HEAD'), self.evidence(), ['src/a.py']))

    def test_forged_origin(self):
        self.revision(); ev = self.evidence(); ev['provenance'] = 'ATTESTED'
        with self.assertRaises(ValueError):
            check.verify_evidence(self.root, self.git('rev-parse','HEAD'), ev, ['src/a.py'])

    def test_bad_or_forged_digest(self):
        self.revision()
        for digest in ['xyz', '0'*64]:
            ev = self.evidence(); ev['artifacts'][0]['sha256'] = digest
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                check.verify_evidence(self.root, self.git('rev-parse','HEAD'), ev, ['src/a.py'])

    def test_missing_evidence(self):
        self.revision(); ev=self.evidence(); ev['artifacts']=[]
        with self.assertRaises(ValueError):
            check.verify_evidence(self.root, self.git('rev-parse','HEAD'), ev, ['src/a.py'])

    def test_wrong_revision_parent(self):
        self.revision(record_changes={'baseline_sha': '0'*40})
        with self.assertRaises(ValueError): self.verify()

    def test_no_baseline_range(self):
        with self.assertRaises(ValueError):
            check.verify_commits(self.root, '0'*40, 'HEAD', legacy_anchor=self.anchor)

    def test_arbitrary_path_rejected(self):
        self.revision(record_changes={'code_files': ['../outside']})
        with self.assertRaises(ValueError): self.verify()

    def test_base_cannot_skip_bad_commit(self):
        self.write('unlogged.py', b'bad')
        self.git('add', '.'); self.git('commit', '-qm', 'bad revision')
        bad = self.git('rev-parse', 'HEAD')
        self.revision()
        with self.assertRaises(ValueError):
            check.verify_commits(self.root, bad, 'HEAD', legacy_anchor=self.anchor)

    def test_valid_multi_commit(self):
        self.revision()
        self.revision({'src/a.py': b'second'})
        self.assertEqual(2, self.verify()['commits'])

    def test_deletion(self):
        self.revision()
        (self.root/'src/a.py').unlink()
        self.revision({'src/b.py': b'replacement'},
                      {'code_files': ['src/a.py', 'src/b.py'],
                       'evidence_paths': ['src/b.py']})
        self.assertEqual(2, self.verify()['commits'])

    def test_merge_rejected(self):
        initial_branch = self.git('branch', '--show-current')
        self.git('checkout', '-qb', 'side')
        self.revision({'src/side.py': b'side'})
        self.git('checkout', initial_branch)
        self.git('merge', '--no-ff', '--no-edit', 'side')
        with self.assertRaises(ValueError): self.verify()

    def test_duplicate_paths(self):
        self.revision(record_changes={'code_files': ['src/a.py', 'src/a.py']})
        with self.assertRaises(ValueError): self.verify()

    def test_missing_newline(self):
        self.revision()
        p=self.root/check.J; p.write_bytes(p.read_bytes().rstrip(b'\n'))
        self.git('add', '.'); self.git('commit', '--amend', '--no-edit', '-q')
        with self.assertRaises(ValueError): self.verify()

    def test_symlink_evidence_does_not_follow_target(self):
        self.revision()
        (self.root/'src/link').symlink_to('/synthetic/protected/no-access')
        self.revision({}, {'code_files': ['src/link'], 'evidence_paths': ['src/link']})
        sha=self.git('rev-parse','HEAD')
        ev=dict(schema_version='1.0',candidate_sha=sha,provenance='NOT_ATTESTED',
                source_mode='synthetic',artifacts=[dict(path='src/link',sha256=hashlib.sha256(
                    b'/synthetic/protected/no-access').hexdigest())])
        self.assertEqual('NOT_ATTESTED',check.verify_evidence(self.root,sha,ev,['src/link']))

    def test_evidence_url_rejected_without_fetch(self):
        self.revision(); ev=self.evidence()
        ev['artifacts'][0]['path']='https://synthetic.invalid/evidence'
        with self.assertRaises(ValueError):
            check.verify_evidence(self.root,self.git('rev-parse','HEAD'),ev,['src/a.py'])

    def test_missing_evidence_fields(self):
        self.revision(); ev=self.evidence(); ev.pop('provenance')
        with self.assertRaises(ValueError):
            check.verify_evidence(self.root,self.git('rev-parse','HEAD'),ev,['src/a.py'])

    def test_unknown_source_mode(self):
        self.revision(); ev=self.evidence(); ev['source_mode']='live'
        with self.assertRaises(ValueError):
            check.verify_evidence(self.root,self.git('rev-parse','HEAD'),ev,['src/a.py'])

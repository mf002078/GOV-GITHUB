"""Post-commit candidate self-report transport, never a Protected Validator."""
import argparse
import hashlib
import json
import pathlib
import sys

if __package__:
    from . import check_worklog as check
else:
    import check_worklog as check


def prepare_manifest(root, expected_sha, pr_base_sha, *, legacy_anchor=check.LEGACY_ANCHOR):
    for label, value in (('expected head', expected_sha), ('PR base', pr_base_sha)):
        if not isinstance(value, str) or not check.SHA.fullmatch(value):
            raise ValueError(label + ' must be a full lowercase commit SHA')
    if check.resolve(root, 'HEAD') != expected_sha:
        raise ValueError('checkout HEAD differs from event candidate SHA')
    if check.git(root, 'status', '--porcelain', '--untracked-files=all').strip():
        raise ValueError('candidate checkout must be clean')
    anchor = check.resolve(root, legacy_anchor)
    # Base compatibility is separate from the immutable validation anchor.
    # Never pass the mutable event base as verifier --base or skip revisions.
    for earlier, later in ((anchor, pr_base_sha), (pr_base_sha, expected_sha)):
        if check.git(root, 'merge-base', earlier, later).decode().strip() != earlier:
            raise ValueError('PR base must descend from anchor and be ancestor of candidate')
    result = check.verify_commits(root, anchor, expected_sha, legacy_anchor=anchor)
    records = [dict(schema_version='1.0', candidate_sha=sha,
                    provenance='NOT_ATTESTED', source_mode='synthetic',
                    artifacts=[dict(path=p, sha256=hashlib.sha256(
                        check.blob(root, sha, p)).hexdigest()) for p in paths])
               for sha, paths in result['evidence_by_commit'].items()]
    # Generation is not acceptance: reject malformed material before transport.
    check.verify_manifest(root, result, records)
    return result, records


def write_manifest(root, output, records):
    output = pathlib.Path(output).resolve()
    if output.is_relative_to(pathlib.Path(root).resolve()):
        raise ValueError('manifest output must be outside candidate checkout')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents stale output from masquerading as this run.
    with output.open('x', encoding='utf-8') as stream:
        json.dump(records, stream, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-sha', required=True)
    parser.add_argument('--pr-base', required=True)
    parser.add_argument('--output', required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        result, records = prepare_manifest(check.ROOT, args.expected_sha, args.pr_base)
        write_manifest(check.ROOT, args.output, records)
        print(json.dumps(dict(candidate_sha=result['candidate_sha'],
                              revisions=result['commits'], provenance='NOT_ATTESTED',
                              gate_a='BLOCKED/UNVERIFIED'), sort_keys=True))
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print('CANDIDATE TRANSPORT BLOCKED', exc)
        return 2


if __name__ == '__main__':
    sys.exit(main())

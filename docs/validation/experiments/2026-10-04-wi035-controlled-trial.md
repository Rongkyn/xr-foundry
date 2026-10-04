# WI-035 controlled contributor-flow trial

Date: 2026-10-04. Result: task discovery, source reading, and a bounded local
candidate succeeded. Required human review and merge remain unproven.

This was a controlled internal fresh-context trial using public repository inputs.
It was not an outside contributor joining the project, an independent tenant or
security boundary, a membership/credit decision, or the WI-010 cold-start proof.
No GitHub contribution was published by the trial. No Unity Editor ran.

## Public inputs and candidate identity

| Artifact | Exact identity |
| --- | --- |
| Fetched upstream `main` | `ff3ac8b0110e5a1b225a88b740460ce2780b11ea` |
| Starting PR112 source | `d27d0cfdf292bbdeb3dd81b5a39f8261c140b52c` in `Rongkyn/xr-foundry` |
| Starting tree | `65264a3229e430918a2520f90a0a2fc6f9ffa63c` |
| Selected task | WI-035, `needs: none`, routine documentation starter |
| Local candidate commit | `7d15079062a3c7fc0c6c1f63b4d00b6bd9b57efa` (not a public contribution reference) |
| Candidate tree | `bd495acc0473e53a195da8266a23e2e83a3c15ff` |
| Exact candidate patch | [2026-10-04-wi035-candidate.patch](2026-10-04-wi035-candidate.patch) |
| Patch SHA-256 | `347ef8c553d817d13b2464715feb7141f3f3ab22fea436f20ed66c894293a671` |

The starting source is the [public PR112 branch revision](https://github.com/Rongkyn/xr-foundry/commit/d27d0cfdf292bbdeb3dd81b5a39f8261c140b52c).

The candidate changes only `docs/standards/settings/README.md` and WI-035's
`status`/`done_proof` in `docs/contributing/work-items.json`. Its local closeout
changes are retained **inside the unapplied patch** to reproduce the complete
candidate tree. Publishing this record does not apply that patch: the active
registry keeps WI-035 **open** with **null** proof, and WI-010 remains open.
The candidate commit's local author metadata is not a contributor identity or
attestation. The tree and patch identify the content without relying on it.

## Discovery and source-derived result

The trial used the public entry guide and these commands:

```bash
python scripts/open_work.py --list-capabilities
python scripts/open_work.py --capability ai_tokens_only --markdown
python scripts/open_work.py --item WI-035 --capability ai_tokens_only --markdown
```

The declaration exposed WI-035, and its generated brief supplied the task's
sources, allowed writes, steps and acceptance without an implementation answer.
The candidate corrected the Settings entry's planned-versus-implemented ambiguity,
linked the two existing package entry points and release instructions, and
separated historical test receipts from later unexecuted changes.

The two Settings receipts record
`7753de2bb10eb6376bc0f1df48bfd74ee3bf1ed9`, not the release tag's target revision
`1b67c092b8c0f38e3c4fcf0b040a8807c97e701e`. Their recorded tuple is Unity Editor
6000.3.19f1, WindowsEditor, Null graphics, Mono, x86_64, Windows host 10.0.26200.
The candidate preserves that distinction and describes tag selectors as
version-pinned; it does not call a movable Git tag intrinsically immutable.
Existing source receipts, rather than this trial, support the historical Editor
claims. This trial added no package, compatibility, renderer, accessibility or
device evidence.

## Observed validation and limits

| Check | Observed result | Evidence level |
| --- | --- | --- |
| Initial full Python suite | 388 tests, OK | Repository tooling/contract execution |
| Final repository validator | PASS, zero errors | Candidate source validation |
| README relative links | Zero missing targets | Local path checks, not web/runtime verification |
| Final diff check | PASS | Patch formatting |
| Candidate patch replay | PASS, exact tree `bd495acc0473e53a195da8266a23e2e83a3c15ff` | Fresh public-source checkout; content identity only |
| Final committed-head merge-readiness | Seven technical checks PASS; overall blocked, exit 1 | Merged-tree repository validation/tests; human review UNKNOWN |
| Unity compilation/EditMode/PlayMode | Not run | No new Unity claim |
| Outside participation, human approval, merge | Not demonstrated | No cold-start, membership or completion claim |

The final readiness command was:

```bash
python scripts/merge_readiness.py --base origin/main --head HEAD --markdown
```

Its base was `ff3ac8b0110e5a1b225a88b740460ce2780b11ea` and candidate HEAD was
`7d15079062a3c7fc0c6c1f63b4d00b6bd9b57efa`. The readiness diff contains 11 files
because it includes PR112's ancestors; the trial delta itself has only two files.
`independent_review` was UNKNOWN without PR metadata. `not_draft` and
`mandated_branch` were informational. Advisory review is not required human
approval, and the blocked verdict must not be presented as permission to merge.
The standalone test log's expected negative-fixture messages are not Unity runs;
the overall Python result is the test evidence described above.

## Reproduce the candidate content locally

From a checkout containing this record, use a new sibling directory. These
commands fetch public source and apply the patch only in the disposable replay
checkout. Do not apply the candidate to the live contribution branch or push its
local registry closeout as part of this validation record.

```bash
set -eu
WI035_RECORD_REPO="$(pwd)"
git clone https://github.com/Lingkyn/xr-foundry.git ../wi035-replay
cd ../wi035-replay
git fetch https://github.com/Rongkyn/xr-foundry.git d27d0cfdf292bbdeb3dd81b5a39f8261c140b52c
git switch --detach FETCH_HEAD
git apply --check "$WI035_RECORD_REPO/docs/validation/experiments/2026-10-04-wi035-candidate.patch"
git apply --index "$WI035_RECORD_REPO/docs/validation/experiments/2026-10-04-wi035-candidate.patch"
test "$(git write-tree)" = bd495acc0473e53a195da8266a23e2e83a3c15ff
git diff --cached --check
python -m venv .venv
.venv/bin/python -m pip install -r scripts/contract-requirements.txt
.venv/bin/python scripts/validate_repository.py --json
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Tree identity proves exact replay of the candidate content, not replay of its
fresh-context provenance or outside independence. A subsequent readiness run must
use a locally committed candidate with the reader's own configured identity;
checking the unchanged starting HEAD would miss the applied candidate.

## Remaining public acceptance

PR112 must first receive its required review and merge before WI-035 exists on
the default branch. This local candidate is review material, not automatic task
completion. A later authorized implementation must be rebased/applied onto the
then-current source and checked again; it must not silently carry an unmerged
PR112 stack. The public outside-contributor exercise still requires an actual
outside contribution, accountable identity, review and merged result before
WI-010 can be completed. Related discovery work remains #65/#66 and the Settings
consumer outcome remains #71; this record closes none of those Issues.

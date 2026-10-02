# Start here: a change in ten minutes

This is the whole path for a routine change (documentation, tests, tooling, or a
non-breaking package change). No claim, no lease, no execution anchor, no
governance window. If you are an Agent, the same steps apply.

## 1. Set up (once, about two minutes)

```text
git clone https://github.com/Lingkyn/xr-foundry
cd xr-foundry
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install -r scripts/contract-requirements.txt
```

For an external contribution, fork `Lingkyn/xr-foundry` on GitHub and add your
fork as a separate push remote (replace `YOUR-LOGIN`). Keep `origin` pointing at
the upstream repository so the readiness check and public-origin evidence use
the expected base:

```text
git remote add fork https://github.com/YOUR-LOGIN/xr-foundry.git
git fetch origin
git switch -c my-change origin/main
git rev-parse HEAD
```

Keep that starting SHA if you later record a cold-start receipt. If you already
have a clone, check `git remote -v` first rather than replacing existing remotes.

A Unity Editor is only needed to run package tests in
Unity; every rule below runs without it.

## 2. Make the change

Work on a branch. Keep the change inside one package or one document set. Add a
line under `## Unreleased` in the affected package `CHANGELOG.md`, and in the root
`CHANGELOG.md` when you touch `scripts/`, `tests/`, `.github/`, or a root contract
file. Do not change a package version, a `maturity` field, a compatibility profile,
or anything under `docs/governance/`, `docs/rfcs/`, or `GOVERNANCE.md` in a
routine change.

Commit your changes before checking `HEAD`; the verdict checks committed work,
not uncommitted edits. Stage only the files intended for this contribution, then:

```text
git commit -m "Describe the bounded change"
```

## 3. Run the one command

```text
git fetch origin
python scripts/merge_readiness.py --base origin/main --head HEAD --markdown
```

It merges your branch onto main in a temporary worktree, runs the repository
contract and every Python test, and prints a table. Fix every `FAIL`. Each contract
error comes with a `hint` in the JSON output of
`python scripts/validate_repository.py --json` that says what to change.

`INFO` rows never block. `unity_evidence: INFO` means your C# has not run in an
Editor; that is allowed for a routine change and is recorded, not hidden.

## 4. Push and open the pull request

Push your committed branch to your fork:

```text
git push -u fork my-change
```

Open a pull request from your fork's `my-change` branch into
`Lingkyn/xr-foundry:main`. Fill in the five lines at the top of the pull-request
template. CI runs the same
command and publishes the verdict on the pull request. A routine change on a
branch covered by an operating mandate merges by GitHub auto-merge once the checks
are green; any other change waits for a maintainer, who reads the same verdict.

## When this page is not enough

- You want something to work on: declare what you bring
  ([`capabilities.md`](capabilities.md)) and run
  `python scripts/open_work.py --capability <id> --markdown`, which narrows the
  open-work board ([`open-work.md`](open-work.md)) to what that declaration can
  finish; or take a self-contained item from [`work-items.md`](work-items.md).
  Export that item's complete instructions with
  `python scripts/open_work.py --item WI-nnn --capability <id> --markdown`
  (replace `WI-nnn` with its real ID). The packet shows prerequisites, readiness,
  paths, every step, and evidence; it reserves nothing. The routine lane needs no claim.
- You want to change a public seam, a package version, or a rule: read
  [`task-hall.md`](task-hall.md) and [`merge-readiness.md`](merge-readiness.md).
- You have a headset and want to produce device evidence: read
  [`../device-lab/README.md`](../device-lab/README.md).
- You have a Unity Editor and want to run the package tests: read
  [`../validation/run-unity-gates.md`](../validation/run-unity-gates.md).
- You want to propose a new reusable system: read
  [`../foundry/README.md`](../foundry/README.md); the current staged example is
  [`../../staging/localization/README.md`](../../staging/localization/README.md).
- You opened your first routine pull request from a fork: you can now fill
  [`cold-start-receipt.template.json`](cold-start-receipt.template.json) with its
  real URL, your starting SHA, observed timings, and actual verdict. Keep
  `merged: false` while the pull request is open. Commit the receipt under
  `docs/validation/cold-start/<id>.json` on the same branch, rerun the verdict,
  and push. After the pull request actually merges, record `merged: true` in a
  follow-up change referencing that same pull request. An open pull request is
  not proof of a completed merge; never predeclare one. These receipts contribute
  to milestone batch 1f's evidence that this page works for a stranger.

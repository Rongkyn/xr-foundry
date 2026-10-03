# Changelog

## [Unreleased]

- Link the pinned Core + Unity quickstart from the package README and
  documentation, including configuration, a copyable consumer script, and
  historical evidence boundaries. No API, package version, or maturity change.
- Added three EditMode tests named by the Persistence coverage map: a same-version
  round trip through an in-memory store, an integrity-provider failure surfacing as
  the Integrity stage before commit, and StageWrite and Flush failures reported as
  distinct results that preserve prior bytes. No runtime change; Editor execution
  is pending.
- Documentation only: expanded `Documentation~/index.md` with the save and load
  pipelines, recovery-policy table, migration graph rules, and commit-capability
  semantics. No API, version, or evidence change.
- Replace scaffold marker with engine-light persistence core implementation.
- Add deterministic save envelope codec, migration pipeline, integrity abstraction, and save coordinator orchestration.
- Add focused editor tests for slot IDs, malformed/future envelopes, checksum corruption, migration rejection paths, fail-closed stage order, and capability mismatch.
- Admit zero-byte raw read candidates so the recovery selector classifies them as malformed envelopes and preserves the primary corruption diagnostic during backup recovery.

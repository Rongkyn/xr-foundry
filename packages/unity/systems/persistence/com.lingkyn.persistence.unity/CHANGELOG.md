# Changelog

## [Unreleased]

- Add the missing Unity adapter namespace import to the LocalFilePersistence
  sample so its config, factory, root provider, and codec names resolve when the
  sample is imported into a consumer project. No runtime API or version change;
  this source correction does not alter the immutable `0.1.0` release.
- Document a pinned two-package quickstart with first-save configuration,
  copyable consumer script, expected results, and explicit evidence limits.
- Implement ScriptableObject authoring validation, JsonUtility plain-DTO codec boundary, persistent-data root policy, local-file `ISaveStore`, recovery inspection, injected file fault seams, and focused EditMode contract tests for checkpoint `PERSISTENCE-UNITY-BUILD`.
- Isolate zero-byte primary, backup, and staging content as individual recovery candidates so one damaged file cannot prevent another readable candidate from reaching the selector.

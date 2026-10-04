using System;
using System.Collections.Generic;
using Lingkyn.Settings.Core;
using Lingkyn.Settings.Unity;
using UnityEngine;

namespace Lingkyn.Settings.Unity.Samples
{
    // Consumer-owned demonstration state. This does not control Unity audio.
    public sealed class SettingsAuthoringHost
    {
        public bool Muted { get; set; }
    }

    public static class SettingsAuthoringExample
    {
        // Retained for callers of the original catalog-conversion example.
        public static SettingsApplyOutcome Run(SettingsCatalogAsset catalog)
            => ApplyMute(catalog, new SettingsAuthoringHost(), true).Outcome;

        // Each invocation creates a fresh coordinator. Production consumers retain
        // one coordinator and initialize host state from its effective snapshot.
        public static SettingsApplyResult ApplyMute(
            SettingsCatalogAsset catalog, SettingsAuthoringHost host,
            bool muted, bool failAfterApply = false)
        {
            if (host == null) throw new ArgumentNullException(nameof(host));
            var applicators = new List<ISettingApplicator> { new MuteApplicator(host) };
            if (failAfterApply) applicators.Add(new RejectAfterMute());
            var created = SettingsUnityFactory.CreateCoordinator(new SettingsUnityFactoryConfig
            {
                Catalog = catalog,
                Applicators = applicators,
            });
            if (!created.Succeeded)
                return SettingsApplyResult.ValidationFailed(0, created.Error);

            var tx = created.Value.BeginTransaction();
            tx.StageSet(new ScopedSettingKey(MustKey("audio.mute"), SettingScope.User), SettingValue.FromBoolean(muted));
            return created.Value.Apply(tx);
        }

        public static SettingsCatalogAsset CreateSampleCatalog()
        {
            var catalog = ScriptableObject.CreateInstance<SettingsCatalogAsset>();
            var mute = ScriptableObject.CreateInstance<SettingDefinitionAsset>();
            mute.key = "audio.mute";
            mute.kind = SettingValueKindRecord.Boolean;
            mute.defaultBoolean = false;
            mute.defaultScope = SettingScopeRecord.User;
            catalog.definitions = new[] { mute };
            return catalog;
        }

        private static SettingKey MustKey(string value) => SettingKey.TryCreate(value).Value;

        private sealed class MuteApplicator : ISettingApplicator
        {
            private readonly SettingsAuthoringHost _host;
            private bool _beforeApply;
            private bool _applied;
            public MuteApplicator(SettingsAuthoringHost host) => _host = host;
            public string ApplicatorId => "sample.mute";
            public int Order => 0;
            public bool CanApply(SettingKey key) => key.Value == "audio.mute";

            public SettingsApplicatorStepResult Apply(IReadOnlyList<SettingChange> changes)
            {
                // Validate before writing: the coordinator rolls back previously
                // successful applicators, not the applicator that reports failure.
                if (changes.Count != 1 || changes[0].Scope != SettingScope.User
                    || !changes[0].HasNewValue || changes[0].NewValue.Kind != SettingValueKind.Boolean)
                    return SettingsApplicatorStepResult.Fail(ApplicatorId, "Expected one User Boolean mute change.");
                _beforeApply = _host.Muted;
                _host.Muted = changes[0].NewValue.BooleanValue;
                _applied = true;
                return SettingsApplicatorStepResult.Success();
            }

            public SettingsApplicatorStepResult Rollback(IReadOnlyList<SettingChange> changes)
            {
                if (_applied) _host.Muted = _beforeApply;
                _applied = false;
                return SettingsApplicatorStepResult.Success();
            }
        }

        private sealed class RejectAfterMute : ISettingApplicator
        {
            public string ApplicatorId => "sample.reject-after-mute";
            public int Order => 1;
            public bool CanApply(SettingKey key) => key.Value == "audio.mute";
            public SettingsApplicatorStepResult Apply(IReadOnlyList<SettingChange> changes)
                => SettingsApplicatorStepResult.Fail(ApplicatorId, "Deliberate sample failure after mute application.");
            public SettingsApplicatorStepResult Rollback(IReadOnlyList<SettingChange> changes)
                => SettingsApplicatorStepResult.Success();
        }
    }
}

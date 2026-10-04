using Lingkyn.Settings.Core;
using NUnit.Framework;
using UnityEngine;

namespace Lingkyn.Settings.Unity.Samples.Tests
{
    public sealed class SettingsAuthoringExampleTests
    {
        private SettingsCatalogAsset _catalog;
        private SettingsAuthoringHost _host;

        [SetUp]
        public void SetUp()
        {
            _catalog = SettingsAuthoringExample.CreateSampleCatalog();
            _host = new SettingsAuthoringHost();
        }

        [TearDown]
        public void TearDown()
        {
            foreach (var definition in _catalog.definitions)
                Object.DestroyImmediate(definition);
            Object.DestroyImmediate(_catalog);
        }

        [Test]
        public void AppliesMuteToObservableConsumerState()
        {
            var result = SettingsAuthoringExample.ApplyMute(_catalog, _host, true);
            Assert.That(result.Outcome, Is.EqualTo(SettingsApplyOutcome.Applied));
            Assert.That(result.CommittedRevision, Is.EqualTo(1));
            Assert.That(_host.Muted, Is.True);
        }

        [TestCase(false)]
        [TestCase(true)]
        public void LaterFailureRestoresActualPriorHostState(bool priorMuted)
        {
            _host.Muted = priorMuted;
            var result = SettingsAuthoringExample.ApplyMute(_catalog, _host, true, failAfterApply: true);
            Assert.That(result.Outcome, Is.EqualTo(SettingsApplyOutcome.ApplicatorFailed));
            Assert.That(result.CommittedRevision, Is.EqualTo(0));
            Assert.That(result.PrimaryFailure.ApplicatorId, Is.EqualTo("sample.reject-after-mute"));
            Assert.That(result.RollbackDiagnostics, Is.Empty);
            Assert.That(_host.Muted, Is.EqualTo(priorMuted));
        }

        [Test]
        public void MissingMuteDefinitionDoesNotApplyHostState()
        {
            _catalog.definitions[0].key = "audio.other";
            var result = SettingsAuthoringExample.ApplyMute(_catalog, _host, true);
            Assert.That(result.Outcome, Is.EqualTo(SettingsApplyOutcome.ValidationFailed));
            Assert.That(_host.Muted, Is.False);
        }

        [Test]
        public void InvalidCatalogPreservesHostStateAndDiagnostic()
        {
            _host.Muted = true;
            var result = SettingsAuthoringExample.ApplyMute(null, _host, false);
            Assert.That(result.Outcome, Is.EqualTo(SettingsApplyOutcome.ValidationFailed));
            Assert.That(result.ValidationError.Message, Is.Not.Empty);
            Assert.That(_host.Muted, Is.True);
        }

        [Test]
        public void NoOpDoesNotSynchronizeDriftedHostState()
        {
            _host.Muted = true;
            var result = SettingsAuthoringExample.ApplyMute(_catalog, _host, false);
            Assert.That(result.Outcome, Is.EqualTo(SettingsApplyOutcome.NoOp));
            Assert.That(result.CommittedRevision, Is.EqualTo(0));
            Assert.That(_host.Muted, Is.True);
        }
    }
}

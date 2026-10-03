using System;
using Lingkyn.Persistence.Core;
using Lingkyn.Persistence.Unity;
using UnityEngine;

namespace Lingkyn.Persistence.Samples
{
    [Serializable]
    public sealed class PlayerProgressDto
    {
        public int level;
        public string checkpoint;
    }

    public static class LocalFilePersistenceExample
    {
        public static SaveResult<PlayerProgressDto> Run(PersistenceUnityConfig config)
        {
            var created = PersistenceUnityFactory.CreateCoordinator(
                config,
                new PersistentDataRootProvider(),
                new JsonUtilitySaveCodec<PlayerProgressDto>(),
                Array.Empty<ISaveMigration<PlayerProgressDto>>());

            if (!created.Succeeded)
            {
                return SaveResult<PlayerProgressDto>.Fail(created.Error.Stage, created.Error.Code, created.Error.Message);
            }

            var coordinator = created.Value;
            var slot = SaveSlotId.TryCreate("slot_main");
            if (!slot.Succeeded)
            {
                return SaveResult<PlayerProgressDto>.Fail(slot.Error.Stage, slot.Error.Code, slot.Error.Message);
            }

            var snapshot = new PlayerProgressDto { level = 3, checkpoint = "town-square" };
            var save = coordinator.Save(slot.Value, snapshot);
            if (!save.Committed)
            {
                return SaveResult<PlayerProgressDto>.Fail(save.Error.Stage, save.Error.Code, save.Error.Message);
            }

            var loaded = coordinator.LoadValidated(slot.Value, _ => SaveResult.Success());
            if (!loaded.Succeeded)
            {
                return SaveResult<PlayerProgressDto>.Fail(loaded.Error.Stage, loaded.Error.Code, loaded.Error.Message);
            }

            return SaveResult<PlayerProgressDto>.Success(loaded.Value.State);
        }
    }
}

"""Fail-closed item briefs must not change the existing best-effort board."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.test_open_work import MODULE, NOW, ROOT, write, write_json


class ItemBriefTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = json.loads((ROOT / MODULE.WORK_ITEMS_FILE).read_text())
        self.payload['items'] = self.payload['items'][:2]
        self.item = self.payload['items'][1]
        self.item.update(status='open', done_proof=None)
        for name in ('work-items.schema.json', 'capability-profiles.schema.json', 'capability-profiles.json'):
            relative = 'docs/contributing/' + name
            write(self.root, relative, (ROOT / relative).read_text())
        profiles = json.loads((self.root / MODULE.CAPABILITY_PROFILES_FILE).read_text())
        for profile in profiles['profiles']:
            write(self.root, profile['start_at'], '# Page\n')
        write(self.root, 'docs/milestones.md', '### Batch 2c\n')
        for item in self.payload['items']:
            for path in item['read_first'] + ([item['done_proof']] if item['done_proof'] else []):
                write(self.root, path, 'Evidence\n')
        for script in ('open_work.py', 'validate_repository.py'):
            write(self.root, 'scripts/' + script, '# script\n')
        self.save()

    def save(self):
        write_json(self.root, MODULE.WORK_ITEMS_FILE.as_posix(), self.payload)

    def packet(self, capability='ai_tokens_only'):
        return MODULE.build_item_brief(self.root, 'WI-002', capability, NOW)

    def cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = MODULE.main(['--root', str(self.root), *args])
        return result, stdout.getvalue(), stderr.getvalue()

    def test_complete_record_and_snapshot_identity(self):
        packet = self.packet()
        self.assertEqual(packet['schema'], 'xr-foundry.item_brief.v1')
        self.assertEqual(packet['item'], self.item)
        self.assertEqual(packet['source_sha256'], hashlib.sha256((self.root / MODULE.WORK_ITEMS_FILE).read_bytes()).hexdigest())
        self.assertTrue(packet['readiness']['ready'])
        self.assertTrue(packet['prerequisites'][0]['complete'])
        self.assertEqual(packet['prerequisites'][0]['done_proof'], self.payload['items'][0]['done_proof'])
        self.assertIn('grant no write', packet['disclaimer'])
        markdown = MODULE.render_item_brief(packet)
        for value in self.item['steps'] + self.item['acceptance']['commands'] + self.item['acceptance']['artifacts']:
            self.assertIn(value, markdown)
        self.assertIn('Ready to start: yes', markdown)

    def test_undeclared_capability_is_never_assumed(self):
        packet = self.packet(None)
        self.assertFalse(packet['readiness']['ready'])
        self.assertIsNone(packet['readiness']['capability_satisfied'])
        self.assertIsNone(packet['capability'])

    def test_status_is_not_availability(self):
        for status in ('blocked', 'in_progress', 'done'):
            with self.subTest(status=status):
                self.item.update(status=status, done_proof='AGENTS.md' if status == 'done' else None)
                self.save()
                packet = self.packet()
                self.assertFalse(packet['readiness']['ready'])
                self.assertIn(status, packet['readiness']['reasons'][0])
                self.assertIn('Ready to start: no', MODULE.render_item_brief(packet))

    def test_pending_dependencies_and_mismatch_are_both_visible(self):
        self.payload['items'][0].update(status='open', done_proof=None)
        self.item['needs'] = 'unity_editor'
        self.item['decision_class'] = 'non_routine'
        self.save()
        packet = self.packet()
        self.assertEqual(packet['readiness']['pending_dependencies'], ['WI-001'])
        self.assertFalse(packet['readiness']['capability_satisfied'])
        self.assertEqual(len(packet['readiness']['reasons']), 2)
        self.assertEqual(packet['item']['decision_class'], 'non_routine')
        self.assertFalse(self.packet('unity_editor')['readiness']['ready'])

    def test_malformed_source_fails_closed(self):
        original = copy.deepcopy(self.payload)
        mutations = (
            lambda p: p['items'].append(copy.deepcopy(p['items'][0])),
            lambda p: p['items'][1].update(depends_on=['WI-999']),
            lambda p: p['items'][0].update(depends_on=['WI-002']),
            lambda p: p['items'][1].update(steps=[]),
            lambda p: p['items'][1].update(status='invented'),
            lambda p: p['items'][1].update(needs='invented'),
            lambda p: p['items'][1].update(allowed_paths=['../escape']),
            lambda p: p['items'][1]['acceptance'].update(commands=['rm -rf /']),
            lambda p: p['items'][0].update(done_proof='missing-proof'),
            lambda p: p['items'][1].update(read_first=['missing-page']),
        )
        for mutation in mutations:
            self.payload = copy.deepcopy(original)
            mutation(self.payload)
            self.save()
            with self.assertRaisesRegex(ValueError, 'invalid work-item source'):
                self.packet()
        write(self.root, MODULE.WORK_ITEMS_FILE.as_posix(), '{invalid')
        self.assertEqual(self.cli('--item', 'WI-002')[0], 1)

    def test_missing_source_and_unknown_item_fail_clearly(self):
        self.assertEqual(self.cli('--item', '')[0], 1)
        code, out, err = self.cli('--item', 'WI-999')
        self.assertEqual(code, 1)
        self.assertEqual(out, '')
        self.assertIn('unknown work item', err)
        (self.root / MODULE.WORK_ITEMS_FILE).unlink()
        self.assertEqual(self.cli('--item', 'WI-002')[0], 1)

    def test_capability_must_come_from_current_valid_source(self):
        with self.assertRaisesRegex(ValueError, 'unknown capability'):
            self.packet('invented')
        path = self.root / MODULE.CAPABILITY_PROFILES_FILE
        profiles = json.loads(path.read_text())
        profiles['profiles'].append(copy.deepcopy(profiles['profiles'][0]))
        write_json(self.root, MODULE.CAPABILITY_PROFILES_FILE.as_posix(), profiles)
        with self.assertRaisesRegex(ValueError, 'duplicate profile id'):
            self.packet()
        self.assertFalse(self.packet(None)['readiness']['ready'])

    def test_json_markdown_output_and_errors(self):
        code, out, err = self.cli('--item', 'WI-002', '--json')
        self.assertEqual((code, err), (0, ''))
        self.assertEqual(json.loads(out)['item'], self.item)
        output = self.root / 'packet.json'
        code, out, err = self.cli('--item', 'WI-002', '--markdown', '--output', str(output))
        self.assertEqual((code, err), (0, ''))
        self.assertIn('# Item brief', out)
        self.assertEqual(json.loads(output.read_text())['item'], self.item)
        self.assertEqual(self.cli('--item', 'WI-002', '--output', str(self.root / 'missing' / 'out.json'))[0], 1)
        for flags in (('--json', '--markdown'), ('--list-capabilities',)):
            with self.assertRaises(SystemExit) as error:
                self.cli('--item', 'WI-002', *flags)
            self.assertEqual(error.exception.code, 2)

    def test_packet_does_not_execute_acceptance_commands(self):
        with patch.object(MODULE, 'git_head', return_value='a' * 40), patch('subprocess.run', side_effect=AssertionError('no execution')):
            self.assertTrue(self.packet()['readiness']['ready'])

    def test_source_changes_during_validation_fail_closed(self):
        from scripts import validate_repository as validator
        original = validator.validate_work_items
        def change_items(root):
            errors = original(root)
            with (root / MODULE.WORK_ITEMS_FILE).open('a') as stream:
                stream.write(' ')
            return errors
        with patch.object(validator, 'validate_work_items', side_effect=change_items):
            with self.assertRaisesRegex(ValueError, 'changed during validation'):
                self.packet()
        original_profiles = validator.validate_capability_profiles
        def change_profiles(root):
            errors = original_profiles(root)
            with (root / MODULE.CAPABILITY_PROFILES_FILE).open('a') as stream:
                stream.write(' ')
            return errors
        with patch.object(validator, 'validate_capability_profiles', side_effect=change_profiles):
            with self.assertRaisesRegex(ValueError, 'changed during capability validation'):
                self.packet()

    def test_real_registry_packets_and_board_schema(self):
        original = json.loads((ROOT / MODULE.WORK_ITEMS_FILE).read_text())
        for item in original['items']:
            packet = MODULE.build_item_brief(ROOT, item['id'], now=NOW)
            self.assertEqual(packet['item'], item)
            self.assertFalse(packet['readiness']['ready'])
        self.assertEqual(MODULE.build_board(ROOT, NOW)['schema'], 'xr-foundry.open_work.v1')


if __name__ == '__main__':
    unittest.main()

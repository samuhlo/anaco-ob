import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'native'))
from core import App, UserError, json_dump
from vaults import discover_vaults


class VaultDiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.app = App(self.root / 'state')

    def tearDown(self):
        self.app.db.close()
        self.temp.cleanup()

    def vault(self, relative):
        path = self.home / relative
        (path / '.obsidian').mkdir(parents=True)
        return path

    def discover(self):
        return discover_vaults(self.home, {})

    def test_registry_finds_external_vault_ignores_stale_paths_and_deduplicates(self):
        external = self.root / 'external-vault'
        external.mkdir()
        alias = self.home / 'linked'
        alias.symlink_to(external, target_is_directory=True)
        json_dump(self.home / '.config/obsidian/obsidian.json', {'vaults': {
            'a': {'path': str(external)}, 'b': {'path': str(alias)},
            'stale': {'path': str(self.root / 'deleted')}, 'invalid': {'path': 'relative'}}})
        found = self.discover()
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['path'], str(external))
        self.assertEqual(found[0]['source'], 'Registrado en Obsidian')

    def test_common_locations_find_multiple_without_reading_notes(self):
        first = self.vault('Second_Brain')
        second = self.vault('Documents/Personal/Study')
        (first / 'secret.md').write_bytes(b'not valid utf8 \xff')
        (self.home / 'SecondBrainEmpty').mkdir()
        self.assertEqual({v['path'] for v in self.discover()}, {str(first), str(second)})
        self.assertFalse((self.app.state / 'config.json').exists())

    def test_flatpak_and_xdg_registries(self):
        external = self.root / 'external'
        external.mkdir()
        data = {'vaults': {'a': {'path': str(external)}}}
        json_dump(self.home / '.var/app/md.obsidian.Obsidian/config/obsidian/obsidian.json', data)
        self.assertEqual(self.discover()[0]['path'], str(external))
        xdg = self.root / 'xdg'
        json_dump(xdg / 'obsidian/obsidian.json', data)
        self.assertEqual(discover_vaults(self.home, {'XDG_CONFIG_HOME': str(xdg)})[0]['path'], str(external))

    def test_malformed_registry_does_not_block_directory_search(self):
        path = self.vault('Notes/Study')
        registry = self.home / '.config/obsidian/obsidian.json'
        registry.parent.mkdir(parents=True)
        for content in ('broken', '[]', '{"vaults": []}', '{"vaults": {"a": null}}'):
            registry.write_text(content)
            self.assertEqual(self.discover()[0]['path'], str(path))

    def test_hidden_and_deep_paths_are_not_recursively_scanned(self):
        self.vault('.private/Hidden')
        self.vault('Documents/a/b/c/deep')
        self.assertEqual(self.discover(), [])

    def test_structure_can_identify_second_brain_without_dot_obsidian(self):
        path = self.home / 'Second_Brain'
        (path / '00_Sistema').mkdir(parents=True)
        (path / '00_Sistema/MANUAL_VAULT.md').write_text('manual')
        (path / '99_Recursos').mkdir()
        self.assertEqual(self.discover()[0]['source'], 'Estructura de Second Brain')

    def test_symlink_aliases_are_deduplicated_and_loops_not_followed(self):
        path = self.vault('Study')
        (self.home / 'alias').symlink_to(path, target_is_directory=True)
        (self.home / 'Documents').symlink_to(self.home, target_is_directory=True)
        self.assertEqual([v['path'] for v in self.discover()], [str(path)])

    def test_settings_accessible_when_old_vault_no_longer_exists(self):
        missing = str(self.home / 'Moved')
        json_dump(self.app.state / 'config.json', {'vault': missing})
        settings = self.app.handle({'action': 'settings'})
        self.assertFalse(settings['vault_available'])
        self.assertEqual(settings['config']['vault'], missing)
        self.assertEqual(settings['config']['vault_mode'], 'manual')
        with self.assertRaises(UserError):
            self.app.handle({'action': 'status'})

    def test_manual_path_accepts_tilde_and_legacy_calls_stay_manual(self):
        path = self.vault('Study')
        with patch.dict('os.environ', {'HOME': str(self.home)}):
            config = self.app.set_config({'vault': '~/Study'})
        self.assertEqual(config['vault'], str(path))
        self.assertEqual(config['vault_mode'], 'manual')
        self.assertEqual(self.app.config()['vault_mode'], 'manual')

    def test_auto_selection_is_persisted_and_discovery_does_not_switch_it(self):
        first, second = self.vault('First'), self.vault('Second')
        self.app.set_config({'vault': str(first), 'vault_mode': 'auto'})
        before = (self.app.state / 'config.json').read_bytes()
        with patch('core.discover_vaults', side_effect=self.discover):
            self.assertEqual(len(self.app.handle({'action': 'discover_vaults'})['vaults']), 2)
        self.assertEqual((self.app.state / 'config.json').read_bytes(), before)
        self.assertEqual(self.app.vault(), first)
        self.app.set_config({'vault': str(second)})
        self.assertEqual(self.app.config()['vault_mode'], 'manual')

    def test_invalid_path_and_mode_leave_saved_settings_intact(self):
        vault = self.vault('Study')
        self.app.set_config({'vault': str(vault)})
        before = (self.app.state / 'config.json').read_bytes()
        for values in ({'vault': str(self.home / 'absent')}, {'vault': ''},
                       {'vault': str(Path.home())}, {'vault_mode': 'unknown'}):
            with self.assertRaises(UserError):
                self.app.set_config(values)
            self.assertEqual((self.app.state / 'config.json').read_bytes(), before)

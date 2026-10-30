import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'native'))
import updater
from core import App, UserError


class UpdaterTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = App(Path(self.temp.name) / 'state')
        self.addCleanup(self.app.db.close)
        self.commands = []

    def command(self, command, *args, **kwargs):
        self.commands.append(command)
        return subprocess.CompletedProcess(command, 0, '1.4.0' if 'print(VERSION)' in command[-1] else '', '')

    def test_rejects_arbitrary_sources_downgrades_and_changed_release(self):
        for target in ['1.4.0;echo danger', '../../evil', 'https://evil.test', '1.4.0-beta', updater.VERSION, None]:
            with self.subTest(target=target), self.assertRaises(UserError):
                updater.install(self.app, target)
        with patch.object(updater, 'latest', return_value='1.5.0'), self.assertRaisesRegex(UserError, 'cambiado'):
            updater.install(self.app, '1.4.0')

    def test_success_preserves_data_and_probes_before_registration(self):
        marker = self.app.state / 'config.json'
        before = marker.read_bytes() if marker.exists() else b'{"private":"unchanged"}'
        marker.write_bytes(before)
        with patch.object(updater, 'latest', return_value='1.4.0'), patch.object(updater.shutil, 'which', return_value='/tools/uv'), patch.object(updater, 'run_command', side_effect=self.command):
            result = updater.install(self.app, '1.4.0')
        self.assertEqual(result['version'], '1.4.0')
        self.assertEqual(marker.read_bytes(), before)
        self.assertIn('anaco-ob @ https://github.com/samuhlo/anaco-ob/archive/refs/tags/v1.4.0.zip', self.commands[1])
        self.assertIn('print(VERSION)', self.commands[2][-1])
        self.assertIn('installer.install', self.commands[3][-2])
        self.assertEqual(len(list((self.app.state / 'runtimes').iterdir())), 1)

    def test_failed_download_keeps_registration_and_releases_lock_for_retry(self):
        with patch.object(updater, 'latest', return_value='1.4.0'), patch.object(updater, 'run_command', side_effect=OSError('offline')), patch('installer.install') as register:
            for _ in range(2):
                with self.assertRaisesRegex(UserError, 'anterior'):
                    updater.install(self.app, '1.4.0')
            register.assert_not_called()
        self.assertEqual(list((self.app.state / 'runtimes').iterdir()), [])

    def test_registration_failure_restores_old_host(self):
        def run(command, *a, **kw):
            if 'installer.install' in ' '.join(command):
                raise RuntimeError('registration failed')
            return self.command(command)
        with patch.object(updater, 'latest', return_value='1.4.0'), patch.object(updater, 'run_command', side_effect=run), patch('installer.install') as register:
            with self.assertRaises(UserError):
                updater.install(self.app, '1.4.0')
            register.assert_called_once_with(self.app.state)

    def test_active_jobs_in_any_vault_prevent_switching(self):
        job = self.app.state / 'jobs' / 'other-vault' / 'job.json'
        job.parent.mkdir(parents=True)
        job.write_text(json.dumps({'status': 'running', 'pid': 1}))
        with patch.object(updater, 'latest', return_value='1.4.0'), patch.object(updater, 'running', return_value=True), patch.object(updater, 'run_command') as run:
            with self.assertRaisesRegex(UserError, 'termine'):
                updater.install(self.app, '1.4.0')
            run.assert_not_called()

    def test_without_uv_uses_separate_venv_and_pip(self):
        with patch.object(updater, 'latest', return_value='1.4.0'), patch.object(updater.shutil, 'which', return_value=None), patch.object(updater, 'run_command', side_effect=self.command):
            updater.install(self.app, '1.4.0')
        self.assertEqual(self.commands[0][:3], [sys.executable, '-m', 'venv'])
        self.assertIn('pip', self.commands[1])
        self.assertNotEqual(self.commands[1][0], sys.executable)

    def test_info_does_not_require_a_vault(self):
        self.assertEqual(self.app.handle({'action': 'update_info'})['version'], updater.VERSION)

    def test_version_mismatch_never_switches_registration(self):
        with patch.object(updater, 'latest', return_value='1.4.0'), patch.object(updater, 'run_command', return_value=subprocess.CompletedProcess([], 0, '0.0.0', '')), patch('installer.install') as register:
            with self.assertRaises(UserError):
                updater.install(self.app, '1.4.0')
            register.assert_not_called()
        self.assertEqual(list((self.app.state / 'runtimes').iterdir()), [])

    def test_exclusive_lock_blocks_a_second_installer(self):
        attempted = False
        def command(argv, *args, **kwargs):
            nonlocal attempted
            if not attempted:
                attempted = True
                with self.assertRaisesRegex(UserError, 'en curso'):
                    updater.install(self.app, '1.4.0')
            return self.command(argv)
        with patch.object(updater, 'latest', return_value='1.4.0'), patch.object(updater, 'run_command', side_effect=command):
            updater.install(self.app, '1.4.0')
        self.assertTrue(attempted)

    def test_latest_rejects_nonstable_or_foreign_tags(self):
        from unittest.mock import MagicMock
        for release in [{'tag_name': 'v1.4.0', 'prerelease': True}, {'tag_name': 'v1.4.0', 'draft': True}, {'tag_name': '../evil'}, {'tag_name': 'v1.4.0-beta.1'}]:
            response = MagicMock()
            response.__enter__.return_value.read.return_value = json.dumps(release).encode()
            with patch.object(updater.urllib.request, 'urlopen', return_value=response), self.assertRaises(UserError):
                updater.latest()

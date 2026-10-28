"""Vault ownership survives configuration changes and interrupted transfers."""
import base64
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'native'))
from core import UserError, json_dump, normalized_url
from jobs import Job
from media import Media
import test_core as core_tests


class VaultIsolationTest(unittest.TestCase):
    setUp = core_tests.CoreTest.setUp
    tearDown = core_tests.CoreTest.tearDown

    def other_vault(self):
        other = self.root / 'Other'
        other.mkdir(exist_ok=True)
        self.app.set_config({'vault': str(other)})
        return other

    def upload(self, asset=False):
        data = b'WEBVTT\n\n00:00.000 --> 00:02.000\nPrivate original source.\n'
        media = Media(self.app)
        message = {'name': 'asset.js' if asset else 'source.vtt', 'size': len(data)}
        if asset:
            message['purpose'] = 'asset'
        identifier = media.begin(message)['upload']
        return media, identifier, data

    def test_upload_cannot_append_or_finish_in_another_vault(self):
        media, identifier, raw = self.upload()
        self.other_vault()
        with self.assertRaises(UserError):
            media.chunk({'upload': identifier, 'offset': 0, 'data': base64.b64encode(raw).decode()})
        self.app.set_config({'vault': str(self.vault)})
        media.chunk({'upload': identifier, 'offset': 0, 'data': base64.b64encode(raw).decode()})
        self.other_vault()
        with self.assertRaises(UserError):
            media.finish({'upload': identifier})
        self.assertTrue((media.upload_dir(identifier) / 'data.part').exists())
        self.app.set_config({'vault': str(self.vault)})
        capture = media.finish({'upload': identifier})
        self.assertEqual(capture['vault'], str(self.vault))

    def test_assets_also_keep_their_vault(self):
        media, identifier, raw = self.upload(asset=True)
        media.chunk({'upload': identifier, 'offset': 0, 'data': base64.b64encode(raw).decode()})
        self.other_vault()
        with self.assertRaises(UserError):
            media.finish_asset({'upload': identifier})
        self.assertTrue(media.upload_dir(identifier).exists())

    def test_legacy_upload_never_acquires_ownership_from_a_retry_job(self):
        media, identifier, raw = self.upload()
        path = media.upload_dir(identifier) / 'meta.json'
        meta = json.loads(path.read_text())
        meta.pop('vault', None)
        json_dump(path, meta)
        with self.assertRaises(UserError):
            media.chunk({'upload': identifier, 'offset': 0, 'data': base64.b64encode(raw).decode()})
        job = Job(self.app, 'a' * 32)
        job.start({'action': 'upload_finish', 'upload': identifier})
        job.update(status='failed')
        with self.assertRaises(UserError):
            media.chunk({'upload': identifier, 'offset': 0, 'data': base64.b64encode(raw).decode()})
        self.assertNotIn('vault', json.loads(path.read_text()))
        self.assertTrue((media.upload_dir(identifier) / 'data.part').exists())

    def test_switching_vault_forgets_the_old_profile_but_same_path_keeps_it(self):
        original = self.app.config()['profile_path']
        self.app.set_config({'vault': str(self.vault)})
        self.assertEqual(self.app.config()['profile_path'], original)
        self.other_vault()
        self.assertNotIn('profile_path', self.app.config())

    def test_worker_can_record_failure_without_moving_its_job_after_external_change(self):
        job = Job(self.app, 'b' * 32)
        job.start({'action': 'draft', 'id': 'c' * 32})
        self.other_vault()
        job.update(status='failed')
        self.assertEqual(json.loads(job.path.read_text())['vault'], str(self.vault))
        with self.assertRaises(UserError):
            job.resume()
        with self.assertRaises(UserError):
            job.cancel()

    def test_request_with_wrong_expected_vault_has_no_capture_side_effect(self):
        self.other_vault()
        with self.assertRaises(UserError):
            self.app.handle({'action': 'capture', 'expected_vault': str(self.vault), 'capture': {
                'url': 'https://example.org', 'title': 'Private', 'text': 'Private text'}})
        self.assertEqual(list((self.app.state / 'captures').glob('*.json')), [])

    def test_one_request_keeps_its_configuration_if_another_process_changes_it(self):
        other = self.root / 'Other'; other.mkdir()
        def change_config(value):
            config = self.app.config()
            config['vault'] = str(other)
            json_dump(self.app.state / 'config.json', config)
            return normalized_url(value)
        with patch('core.normalized_url', side_effect=change_config):
            capture = self.app.handle({'action': 'capture', 'expected_vault': str(self.vault), 'capture': {
                'url': 'https://example.org', 'title': 'Original', 'text': 'Retained in original vault'}})
        self.assertEqual(capture['vault'], str(self.vault))
        self.assertEqual(self.app.vault(), other)

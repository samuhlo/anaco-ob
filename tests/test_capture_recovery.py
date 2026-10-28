import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'native'))
from core import UserError
from jobs import Job
import test_core as core_tests
from records import RecordError, read_record


class CaptureRecoveryTest(unittest.TestCase):
    setUp = core_tests.CoreTest.setUp
    tearDown = core_tests.CoreTest.tearDown
    capture = core_tests.CoreTest.capture

    def broken(self, raw=b'{broken'):
        identifier = 'f' * 32
        path = self.app.state / 'captures' / (identifier + '.json')
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(raw)
        return identifier, path

    def test_bad_records_do_not_hide_healthy_pending_captures(self):
        healthy = self.capture()
        for raw in (b'{broken', b'[]', b'null', b'\xff', b'{"status":"pending"}'):
            with self.subTest(raw=raw):
                identifier, path = self.broken(raw)
                status = self.app.handle({'action': 'status'})
                self.assertEqual([c['id'] for c in status['pending']], [healthy['id']])
                report = status['storage_health']['captures']
                self.assertEqual(report['count'], 1)
                self.assertEqual(report['records'][0]['id'], identifier)
                self.assertEqual(path.read_bytes(), raw)

    def test_direct_load_has_an_actionable_error_and_retains_original(self):
        identifier, path = self.broken()
        before = path.read_bytes()
        with self.assertRaisesRegex(UserError, identifier):
            self.app.handle({'action': 'load', 'id': identifier})
        self.assertEqual(path.read_bytes(), before)

    def test_repair_restores_visibility_without_a_reset_or_migration(self):
        c = self.capture()
        path = self.app.state / 'captures' / (c['id'] + '.json')
        original = path.read_bytes()
        path.write_bytes(b'{broken')
        self.assertEqual(self.app.handle({'action': 'status'})['storage_health']['captures']['count'], 1)
        path.write_bytes(original)
        status = self.app.handle({'action': 'status'})
        self.assertEqual(status['storage_health']['captures']['count'], 0)
        self.assertEqual(status['pending'][0]['id'], c['id'])

    def test_corrupt_job_does_not_disconnect_the_service(self):
        job = Job(self.app, 'a' * 32)
        job.start({'action': 'draft', 'id': 'b' * 32})
        job.path.write_text('[]')
        status = self.app.handle({'action': 'status'})
        self.assertEqual(status['jobs'], [])
        self.assertEqual(status['storage_health']['jobs']['count'], 1)
        with self.assertRaises(UserError):
            self.app.handle({'action': 'resume_job', 'job': 'a' * 32})
        self.assertEqual(job.path.read_text(), '[]')

    def test_invalid_configuration_never_falls_back_or_overwrites_itself(self):
        path = self.app.state / 'config.json'
        for raw in (b'{broken', b'[]'):
            path.write_bytes(raw)
            with self.assertRaises(UserError):
                self.app.handle({'action': 'configure', 'values': {'provider': 'manual'}})
            self.assertEqual(path.read_bytes(), raw)

    def test_diagnostics_are_bounded_and_do_not_include_source_text(self):
        c = self.capture(text='PRIVATE CONTENT MUST NOT APPEAR IN DIAGNOSTICS')
        data = self.app.load(c['id'])
        for i in range(30):
            path = self.app.state / 'captures' / (f'{i:032x}' + '.json')
            path.write_text(json.dumps({**data, 'id': None}))
        report = self.app.handle({'action': 'status'})['storage_health']['captures']
        self.assertEqual(report['count'], 30)
        self.assertLessEqual(len(report['records']), 20)
        self.assertNotIn('PRIVATE', json.dumps(report))

    def test_mismatched_id_is_not_offered_as_another_capture(self):
        c = self.capture()
        _, path = self.broken()
        path.write_text(json.dumps(self.app.load(c['id'])))
        status = self.app.handle({'action': 'status'})
        self.assertEqual([item['id'] for item in status['pending']], [c['id']])
        self.assertEqual(status['storage_health']['captures']['count'], 1)


class RecordReaderTest(unittest.TestCase):
    def test_read_limit_and_permission_failures_have_stable_codes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'record.json'
            path.write_bytes(b'{"long": "value"}')
            with self.assertRaises(RecordError) as caught:
                read_record(path, limit=8)
            self.assertEqual(caught.exception.code, 'too_large')
            with patch.object(Path, 'open', side_effect=PermissionError('private path')):
                with self.assertRaises(RecordError) as caught:
                    read_record(path)
            self.assertEqual(str(caught.exception), 'unreadable')
            self.assertEqual(path.read_bytes(), b'{"long": "value"}')

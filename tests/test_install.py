import json
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from install import migrate_state


class StateMigrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.legacy = self.root / 'zen-second-brain'
        self.target = self.root / 'anaco-ob'
        self.legacy.mkdir()
        (self.legacy / 'config.json').write_text(json.dumps({'vault': '/my/vault', 'model': 'my-model'}))
        (self.legacy / 'pending.json').write_text(json.dumps({'input': str(self.legacy / 'audio.bin')}))
        (self.legacy / 'audio.bin').write_bytes(b'existing audio')

    def tearDown(self):
        self.temp.cleanup()

    def test_data_absolute_job_paths_and_live_database_writer_survive_move(self):
        before = {p.name: p.read_bytes() for p in self.legacy.iterdir()}
        database = sqlite3.connect(self.legacy / 'history.sqlite')
        try:
            database.execute('CREATE TABLE saves (path TEXT)')
            database.execute('INSERT INTO saves VALUES (?)', ('old-note.md',))
            database.commit()
            self.assertTrue(migrate_state(self.legacy, self.target))
            for name, content in before.items():
                self.assertEqual((self.target / name).read_bytes(), content)
            pending = json.loads((self.target / 'pending.json').read_text())
            self.assertEqual(Path(pending['input']).read_bytes(), b'existing audio')
            database.execute('INSERT INTO saves VALUES (?)', ('new-note.md',))
            database.commit()
            with closing(sqlite3.connect(self.target / 'history.sqlite')) as check:
                self.assertEqual(check.execute('SELECT path FROM saves').fetchall(), [('old-note.md',), ('new-note.md',)])
        finally:
            database.close()

    def test_reinstall_keeps_data_and_legacy_alias(self):
        migrate_state(self.legacy, self.target)
        (self.target / 'new-capture.json').write_text('new capture')
        self.assertFalse(migrate_state(self.legacy, self.target))
        self.assertEqual(self.legacy.resolve(), self.target)
        self.assertEqual((self.legacy / 'new-capture.json').read_text(), 'new capture')

    def test_existing_destination_is_not_overwritten_or_merged(self):
        self.target.mkdir()
        (self.target / 'config.json').write_text('current settings')
        self.assertFalse(migrate_state(self.legacy, self.target))
        self.assertEqual((self.target / 'config.json').read_text(), 'current settings')
        self.assertFalse(self.legacy.is_symlink())
        self.assertTrue((self.legacy / 'pending.json').is_file())

    def test_alias_failure_restores_original_location(self):
        with patch.object(Path, 'symlink_to', side_effect=OSError('alias unavailable')):
            with self.assertRaises(OSError):
                migrate_state(self.legacy, self.target)
        self.assertTrue((self.legacy / 'config.json').is_file())
        self.assertFalse(self.target.exists())

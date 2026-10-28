"""Exercise launcher paths through actual shells and binary stdio."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'native'))
import installer
from processes import ManagedProcess


class LauncherPathsTest(unittest.TestCase):
    def round_trip(self, name, delayed=False):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = root / name
            state.mkdir()
            code = root / ('code %PATH% ! ' + name)
            code.mkdir()
            observed = root / 'observed.json'
            host = code / 'host.py'
            host.write_text(
                'import json,os,sys\nfrom pathlib import Path\n'
                f'Path({str(observed)!r}).write_text(json.dumps(os.environ["ANACO_OB_STATE"]),encoding="utf-8")\n'
                'data=sys.stdin.buffer.read()\nsys.stdout.buffer.write(data)\nsys.stdout.buffer.flush()\n',
                encoding='utf-8')
            with patch.object(installer, '__file__', str(code / 'installer.py')):
                launcher = installer.launcher(state)
            payload = bytes(range(256)) * 8
            command = [os.environ['COMSPEC'], '/d', '/v:on', '/c', str(launcher)] if delayed else [str(launcher)]
            with ManagedProcess(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                shell=os.name == 'nt' and not delayed, cwd=root) as process:
                stdout, stderr = process.communicate(input=payload, timeout=30)
                result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
            self.assertEqual(result.stdout, payload)
            self.assertEqual(json.loads(observed.read_text(encoding='utf-8')), str(state.resolve()))
            self.assertFalse((root / 'AUDIT_MARKER').exists())

    def test_spaces_unicode_and_metacharacters_are_literal(self):
        self.round_trip('café 雪 & (data) $vault' if os.name == 'nt' else 'café 雪 %PATH% ! & (data) $vault')

    @unittest.skipIf(os.name == 'nt', 'These file names are POSIX-specific')
    def test_command_substitution_and_quotes_are_not_executed(self):
        self.round_trip('data$(touch AUDIT_MARKER) `touch AUDIT_MARKER` \' "')

    @unittest.skipUnless(os.name == 'nt', 'Exercises cmd.exe delayed expansion')
    def test_windows_launcher_disables_inherited_delayed_expansion(self):
        self.round_trip('café 雪 (data)', delayed=True)

    def test_windows_rejects_ambiguous_entry_paths_before_writing_a_launcher(self):
        with tempfile.TemporaryDirectory() as temp:
            for name in ('literal%PATH%', 'literal!PATH!'):
                state = Path(temp) / name
                state.mkdir()
                with self.assertRaisesRegex(ValueError, '--state'):
                    installer.launcher(state, platform='win32')
                self.assertEqual(list(state.iterdir()), [])


if __name__ == '__main__':
    unittest.main()

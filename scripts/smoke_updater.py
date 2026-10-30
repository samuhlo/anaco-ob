#!/usr/bin/env python3
"""Real Linux/macOS side-by-side install and native-host probe, isolated from user data.

Only the package source and registration home are redirected to test fixtures.
Run explicitly: python scripts/smoke_updater.py (requires uv or working pip).
"""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'native'))
import updater
from core import App, VERSION


def main():
    if os.name == 'nt':
        raise SystemExit('This smoke test isolates registration via a POSIX home directory; Windows is covered by installer unit tests.')
    with tempfile.TemporaryDirectory(prefix='anaco-updater-') as temp:
        home = Path(temp) / 'home'
        home.mkdir()
        app = App(Path(temp) / 'state')
        vault = Path(temp) / 'vault'
        vault.mkdir()
        before = {**app.config(), 'vault': str(vault), 'vault_mode': 'manual'}
        app.set_config(before)
        config = (app.state / 'config.json').read_bytes()
        original = updater.run_command
        def command(argv, *args, **kwargs):
            argv = list(argv)
            argv = [f'anaco-ob @ {ROOT.as_uri()}' if value.startswith('anaco-ob @ https:') else value for value in argv]
            for i, value in enumerate(argv):
                if 'installer.install(sys.argv[1])' in value:
                    argv[i] = value.replace('installer.install(sys.argv[1])', 'installer.install(sys.argv[1], home=sys.argv[2])')
                    argv.append(str(home))
                    break
            return original(argv, *args, **kwargs)
        try:
            with patch.object(updater, 'VERSION', '1.3.1'), patch.object(updater, 'latest', return_value=VERSION), patch.object(updater, 'run_command', side_effect=command):
                result = updater.install(app, VERSION)
            assert result['version'] == VERSION
            assert (app.state / 'config.json').read_bytes() == config
            payload = json.dumps({'action': 'update_info', 'requestId': 'smoke'}).encode()
            response = subprocess.run([str(app.state / 'native-host')], input=struct.pack('=I', len(payload)) + payload, capture_output=True, check=True, timeout=30)
            size = struct.unpack('=I', response.stdout[:4])[0]
            reply = json.loads(response.stdout[4:4 + size])
            assert reply['ok'] and reply['result']['version'] == VERSION, reply
            print(json.dumps({'passed': True, 'version': VERSION, 'real_install': True, 'native_round_trip': True, 'settings_preserved': True}))
        finally:
            app.db.close()


if __name__ == '__main__':
    main()

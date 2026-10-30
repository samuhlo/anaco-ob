"""Install official stable releases beside the running service, then switch hosts."""
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import urllib.request

from core import VERSION, UserError
from jobs import run_command, running

API = 'https://api.github.com/repos/samuhlo/anaco-ob/releases/latest'


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise UserError('La versión de actualización no es válida.')
    return tuple(map(int, value.split('.')))


def latest():
    request = urllib.request.Request(API, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Anaco-updater'})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.loads(response.read(1_000_001))
    tag = data.get('tag_name', '')
    if data.get('draft') or data.get('prerelease') or not re.fullmatch(r'v\d+\.\d+\.\d+', tag):
        raise UserError('La versión de actualización no es válida.')
    return tag[1:]


def info():
    return {'version': VERSION, 'can_update': True}


def install(app, target):
    # Never accept a download URL or executable from the extension or release metadata.
    if version(target) <= version(VERSION):
        raise UserError('El servicio ya tiene esta versión o una posterior.')
    try:
        if latest() != target:
            raise UserError('La versión publicada ha cambiado. Busca actualizaciones de nuevo.')
    except UserError:
        raise
    except Exception as exc:
        raise UserError('No se pudo comprobar la versión oficial. Inténtalo de nuevo.') from exc
    for path in (app.state / 'jobs').glob('*/job.json'):
        try:
            if running(json.loads(path.read_text(encoding='utf-8'))):
                raise UserError('Espera a que termine el trabajo antes de actualizar.')
        except (OSError, ValueError, TypeError, AttributeError):
            continue
    # Exclusive filesystem lock also covers other browser profiles/processes.
    lock = (app.state / 'service-update.lock').open('a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            if lock.seek(0, 2) == 0:
                lock.write(b'0'); lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        lock.close()
        raise UserError('Ya hay una actualización en curso.') from exc
    runtime = None
    switching = False
    def run(command):
        result = run_command(command, lambda: None, timeout=600, text=True)
        if result.returncode:
            raise RuntimeError('update command failed')
        return result.stdout.strip()
    try:
        root = (app.state / 'runtimes').resolve()
        root.mkdir(exist_ok=True)
        runtime = Path(tempfile.mkdtemp(prefix=target + '-', dir=root))
        python = runtime / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        uv = shutil.which('uv')
        if uv:
            run([uv, 'venv', '--python', sys.executable, str(runtime)])
            install_command = [uv, 'pip', 'install', '--python', str(python)]
        else:
            run([sys.executable, '-m', 'venv', str(runtime)])
            install_command = [str(python), '-m', 'pip', 'install', '--disable-pip-version-check']
        source = 'https://github.com/samuhlo/anaco-ob/archive/refs/tags/v' + target + '.zip'
        run([*install_command, 'anaco-ob @ ' + source])
        # Probe the installed code before altering any browser registration.
        actual = run([str(python), '-I', '-c', 'import anaco_ob.cli; from core import VERSION; print(VERSION)'])
        if actual != target:
            raise RuntimeError('installed version mismatch')
        switching = True
        # Register only; do not rewrite the user's settings as the install CLI does.
        run([str(python), '-I', '-c', 'import sys; import anaco_ob.cli; import installer; installer.install(sys.argv[1])', str(app.state.resolve())])
        return {'version': target, 'restart_required': True}
    except Exception as exc:
        if switching:
            import installer
            installer.install(app.state)
        if runtime:
            shutil.rmtree(runtime, ignore_errors=True)
        raise UserError('No se pudo instalar la actualización. El servicio anterior sigue disponible. Reintenta desde Opciones.') from exc
    finally:
        lock.close()  # OS releases the lock even if the host crashes.

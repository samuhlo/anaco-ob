#!/usr/bin/env python3
"""Talk to the registered launcher exactly as the browser does: framed JSON on stdio."""
import json
from pathlib import Path
import struct
import subprocess
import sys


def registered_manifest():
    """Where `anaco-ob install` registered the host for this system."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "native"))
    import installer
    if installer.system() == "win32":
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, installer.REGISTRY_KEY) as key:
            return winreg.QueryValue(key, None)
    return Path.home() / installer.FOLDERS[installer.system()][0] / f"{installer.HOST_NAME}.json"


def main(manifest_path=None):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'native'))
    from processes import ManagedProcess
    manifest = json.loads(Path(manifest_path or registered_manifest()).read_text())
    message = json.dumps({"requestId": "smoke", "action": "settings"}).encode()
    with ManagedProcess([manifest['path']], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        shell=manifest['path'].endswith('.bat')) as child:
        stdout, stderr = child.communicate(input=struct.pack('=I', len(message)) + message, timeout=60)
        process = subprocess.CompletedProcess(child.args, child.returncode, stdout, stderr)
    size = struct.unpack("=I", process.stdout[:4])[0]
    reply = json.loads(process.stdout[4:4 + size])
    assert reply.get("ok") and reply.get("requestId") == "smoke", (reply, process.stderr[-500:])
    print("El servicio responde:", sorted(reply["result"]))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)

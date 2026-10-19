"""Register the local service with Firefox and Zen on Linux, macOS and Windows.

Writes a launcher and the Native Messaging manifests for the current user only.
Never touches browser profiles or vault notes.
"""
import json
import os
from pathlib import Path
import shutil
import sys

HOST_NAME = "org.samuh.anaco_ob"
EXTENSION_ID = "anaco-ob@samuhlo"
REGISTRY_KEY = rf"Software\Mozilla\NativeMessagingHosts\{HOST_NAME}"
# Zen reads its own folder on some releases and Mozilla's on others: register both.
FOLDERS = {
    "linux": [".mozilla/native-messaging-hosts", ".config/zen/native-messaging-hosts"],
    "darwin": ["Library/Application Support/Mozilla/NativeMessagingHosts", "Library/Application Support/zen/NativeMessagingHosts"],
}


def system(platform=None):
    platform = platform or sys.platform
    return "win32" if platform.startswith("win") else "darwin" if platform == "darwin" else "linux"


def default_state(platform=None, home=None, environ=None):
    home, environ = Path(home or Path.home()), os.environ if environ is None else environ
    kind = system(platform)
    if kind == "win32":
        return Path(environ.get("APPDATA") or home / "AppData/Roaming") / "anaco-ob"
    if kind == "darwin":
        return home / "Library/Application Support/anaco-ob"
    return Path(environ.get("XDG_DATA_HOME") or home / ".local/share") / "anaco-ob"


class WindowsRegistry:
    """HKEY_CURRENT_USER, where Firefox looks up per-user hosts."""

    def set(self, key, value):
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as handle:
            winreg.SetValueEx(handle, "", 0, winreg.REG_SZ, value)

    def delete(self, key):
        import winreg
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
        except FileNotFoundError:
            pass


def launcher(state, platform=None):
    """A launcher that starts host.py with this interpreter and state folder."""
    host = Path(__file__).resolve().with_name("host.py")
    state = Path(state).resolve()
    if system(platform) == "win32":
        path = state / "native-host.bat"
        path.write_text(f'@echo off\r\nset "ANACO_OB_STATE={state}"\r\n"{sys.executable}" "{host}" %*\r\n')
    else:
        path = state / "native-host"
        quote = lambda value: '"' + str(value).replace('"', '\\"') + '"'
        path.write_text(f"#!/bin/sh\nexport ANACO_OB_STATE={quote(state)}\nexec {quote(sys.executable)} {quote(host)} \"$@\"\n")
        path.chmod(0o700)
    return path


def manifest(path):
    return {"name": HOST_NAME, "description": "Anaco local service", "path": str(path), "type": "stdio", "allowed_extensions": [EXTENSION_ID]}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def install(state, platform=None, home=None, registry=None):
    kind, home = system(platform), Path(home or Path.home())
    state = Path(state)
    state.mkdir(parents=True, exist_ok=True)
    path = launcher(state, kind)
    registered = []
    if kind == "win32":
        target = state.resolve() / f"{HOST_NAME}.json"
        write_json(target, manifest(path))
        (registry or WindowsRegistry()).set(REGISTRY_KEY, str(target))
        registered.append(rf"HKCU\{REGISTRY_KEY}")
    else:
        for folder in FOLDERS[kind]:
            target = home / folder / f"{HOST_NAME}.json"
            write_json(target, manifest(path))
            registered.append(str(target))
    return {"launcher": str(path), "registered": registered}


def uninstall(state, platform=None, home=None, registry=None, purge=False):
    kind, home, state = system(platform), Path(home or Path.home()), Path(state)
    removed = []
    if kind == "win32":
        (registry or WindowsRegistry()).delete(REGISTRY_KEY)
        removed.append(rf"HKCU\{REGISTRY_KEY}")
        targets = [state / f"{HOST_NAME}.json"]
    else:
        targets = [home / folder / f"{HOST_NAME}.json" for folder in FOLDERS[kind]]
    for target in targets + [state / "native-host", state / "native-host.bat"]:
        if target.exists():
            target.unlink()
            removed.append(str(target))
    if purge and state.exists():
        shutil.rmtree(state)
        removed.append(str(state))
    return {"removed": removed}

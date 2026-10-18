#!/usr/bin/env python3
"""Install the user-scoped native host; never touches browser profiles or vault notes."""
import argparse
import json
from pathlib import Path
import shlex
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "native"))
from core import App, STATE, json_dump


def migrate_state(legacy, target):
    """Move existing data once; old job paths keep resolving via an alias."""
    if target.exists() or target.is_symlink() or not legacy.is_dir() or legacy.is_symlink():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    legacy.rename(target)
    try:
        legacy.symlink_to(target, target_is_directory=True)
    except OSError:
        target.rename(legacy)
        raise
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, default=STATE)
    parser.add_argument("--vault", type=Path)
    args = parser.parse_args()
    default_install = args.state.resolve() == (Path.home() / ".local/share/anaco-ob").resolve()
    if default_install and migrate_state(Path.home() / ".local/share/zen-second-brain", args.state.resolve()):
        print("Configuración, capturas e historial migrados a:", args.state)
    app = App(args.state)
    cfg = app.config()
    if args.vault:
        cfg["vault"] = str(args.vault.resolve())
        cfg["vault_mode"] = "manual"
    cfg["codex"] = shutil.which("codex") or cfg["codex"]
    json_dump(args.state / "config.json", cfg)
    launcher = args.state.resolve() / "native-host"
    launcher.write_text("#!/bin/sh\nexport ANACO_OB_STATE=" + shlex.quote(str(args.state.resolve())) +
                        "\nexec " + shlex.quote(sys.executable) + " " + shlex.quote(str(ROOT / "native/host.py")) + "\n")
    launcher.chmod(0o700)
    # Keep the installation ID so renaming preserves browser preferences and edits.
    manifest = {"name": "org.samuh.anaco_ob", "description": "Anaco local host",
                "path": str(launcher), "type": "stdio", "allowed_extensions": ["anaco-ob@samuhlo"]}
    for directory in (Path.home() / ".mozilla/native-messaging-hosts", Path.home() / ".config/zen/native-messaging-hosts"):
        target = directory / "org.samuh.anaco_ob.json"
        json_dump(target, manifest)
        print("Registrado:", target)
        # An already loaded version can reconnect until Anaco is reloaded.
        legacy = directory / "org.samuh.second_brain.json"
        if default_install and legacy.exists():
            json_dump(legacy, {**manifest, "name": "org.samuh.second_brain"})
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    version = json.loads((ROOT / "extension/manifest.json").read_text())["version"]
    package = dist / f"anaco-ob-{version}.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((ROOT / "extension").rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(ROOT / "extension").as_posix())
    print("Extensión preparada:", package)
    print("Vault configurado:", cfg["vault"])
    print("En Zen: about:debugging#/runtime/this-firefox → Cargar complemento temporal → extension/manifest.json")
    print("Guía de prueba:", ROOT / "PRUEBA.md")


if __name__ == "__main__":
    main()

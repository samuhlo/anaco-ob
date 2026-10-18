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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, default=STATE)
    parser.add_argument("--vault", type=Path)
    args = parser.parse_args()
    app = App(args.state)
    cfg = app.config()
    if args.vault:
        cfg["vault"] = str(args.vault.resolve())
        cfg["vault_mode"] = "manual"
    cfg["codex"] = shutil.which("codex") or cfg["codex"]
    json_dump(args.state / "config.json", cfg)
    launcher = args.state.resolve() / "native-host"
    launcher.write_text("#!/bin/sh\nexport ZEN_BRAIN_STATE=" + shlex.quote(str(args.state.resolve())) +
                        "\nexec " + shlex.quote(sys.executable) + " " + shlex.quote(str(ROOT / "native/host.py")) + "\n")
    launcher.chmod(0o700)
    manifest = {"name": "org.samuh.second_brain", "description": "Second Brain Capture local host",
                "path": str(launcher), "type": "stdio", "allowed_extensions": ["second-brain-capture@samuh.local"]}
    for directory in (Path.home() / ".mozilla/native-messaging-hosts", Path.home() / ".config/zen/native-messaging-hosts"):
        target = directory / "org.samuh.second_brain.json"
        json_dump(target, manifest)
        print("Registrado:", target)
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    version = json.loads((ROOT / "extension/manifest.json").read_text())["version"]
    package = dist / f"second-brain-capture-{version}.zip"
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

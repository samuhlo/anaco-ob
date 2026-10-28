"""anaco-ob: install, check and run the local service of the Anaco extension."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

# Installed wheel: anaco_ob/native. Development checkout: ../native.
HERE = Path(__file__).resolve().parent
NATIVE = HERE / "native" if (HERE / "native").is_dir() else HERE.parent / "native"
sys.path.insert(0, str(NATIVE))

from core import App, STATE, json_dump  # noqa: E402
import installer  # noqa: E402

MEDIA = ["faster-whisper==1.2.1", "av==16.1.0"]


def install(args):
    app = App(args.state)
    config = app.config()
    if args.vault:
        config["vault"], config["vault_mode"] = str(args.vault.expanduser().resolve()), "manual"
    config["codex"] = shutil.which("codex") or config["codex"]
    json_dump(Path(args.state) / "config.json", config)
    result = installer.install(args.state)
    print("Servicio registrado para Firefox y Zen:")
    for target in result["registered"]:
        print("  " + target)
    print("Datos locales:", Path(args.state).resolve())
    print("Siguiente paso: abre Anaco en el navegador y confirma el perfil de tu vault en Opciones.")


def uninstall(args):
    result = installer.uninstall(args.state, purge=args.purge)
    for target in result["removed"]:
        print("Eliminado:", target)
    if not args.purge:
        print("Tus datos locales se conservan en", Path(args.state).resolve(), "· usa --purge para borrarlos.")


def doctor(args):
    """Print what is installed and what is missing, with the fix for each."""
    checks = [("Python " + ".".join(map(str, sys.version_info[:3])), sys.version_info >= (3, 11), "Instala Python 3.11 o superior.")]
    launcher = Path(args.state) / "native-host"
    if installer.system() == "win32":
        try:
            manifest = json.loads((Path(args.state) / (installer.HOST_NAME + '.json')).read_text(encoding='utf-8'))
            launcher = Path(manifest['path'])
        except (OSError, ValueError, KeyError, TypeError):
            launcher = Path(args.state) / 'native-host.bat'
    checks.append(("Servicio registrado", launcher.is_file(), "Ejecuta: anaco-ob install"))
    checks.append(("Codex (IA con ChatGPT)", bool(shutil.which("codex")), "Opcional: instala Codex y ejecuta 'codex login', o usa otro proveedor."))
    for tool, purpose in (("pdftotext", "PDF"), ("ffmpeg", "vídeo y audio"), ("yt-dlp", "vídeos de plataformas")):
        checks.append((f"{tool} ({purpose})", bool(shutil.which(tool)), f"Opcional: instala {tool} para {purpose}."))
    venv = Path(args.state) / "media-venv"
    checks.append(("Transcripción local (Whisper)", venv.is_dir(), "Opcional: ejecuta anaco-ob install-media"))
    for label, ok, fix in checks:
        print(("✓ " if ok else "✗ ") + label + ("" if ok else " — " + fix))
    return 0 if checks[0][1] and checks[1][1] else 1


def install_media(args):
    venv = Path(args.state) / "media-venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    python = venv / ("Scripts/python.exe" if installer.system() == "win32" else "bin/python")
    subprocess.run([str(python), "-m", "pip", "install", "--quiet", *MEDIA], check=True)
    print("Motor de transcripción instalado en", venv, "· el modelo se descarga al transcribir el primer archivo.")


def host(_args):
    import host as native_host
    native_host.main()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="anaco-ob", description="Servicio local de Anaco para Zen y Firefox.")
    parser.add_argument("--state", type=Path, default=STATE, help="Carpeta de datos del servicio")
    commands = parser.add_subparsers(dest="command", required=True)
    step = commands.add_parser("install", help="Registra el servicio para Firefox y Zen")
    step.add_argument("--vault", type=Path, help="Ruta de tu vault de Obsidian")
    step.set_defaults(run=install)
    step = commands.add_parser("uninstall", help="Quita el registro del servicio")
    step.add_argument("--purge", action="store_true", help="Borra también los datos locales")
    step.set_defaults(run=uninstall)
    commands.add_parser("doctor", help="Comprueba la instalación").set_defaults(run=doctor)
    commands.add_parser("install-media", help="Instala la transcripción local con Whisper").set_defaults(run=install_media)
    commands.add_parser("host", help="Arranca el servicio (lo usa el navegador)").set_defaults(run=host)
    args = parser.parse_args(argv)
    try:
        return args.run(args) or 0
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())

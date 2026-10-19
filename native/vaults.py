"""Find local vaults from Obsidian's registry and a bounded directory search.

Detection reads paths and directory names only; it never opens notes or changes
Obsidian's configuration. An explicit path can always be entered instead.
"""
import json
import os
from collections import deque
from pathlib import Path
from translation import t


def discover_vaults(home=None, environ=None):
    home = Path(home) if home is not None else Path.home()
    environ = os.environ if environ is None else environ
    registry_paths = [
        Path(environ.get("XDG_CONFIG_HOME", str(home / ".config"))) / "obsidian/obsidian.json",
        home / ".config/obsidian/obsidian.json",
        home / ".var/app/md.obsidian.Obsidian/config/obsidian/obsidian.json",
        home / "Library/Application Support/obsidian/obsidian.json",
    ]
    if environ.get("APPDATA"):
        registry_paths.append(Path(environ["APPDATA"]) / "obsidian/obsidian.json")
    found = {}

    def add(path, source, registered=False):
        try:
            path = Path(path).expanduser()
            if not path.is_absolute():
                return
            path = path.resolve(strict=True)
            if not path.is_dir() or path in (home.resolve(), Path(path.anchor)):
                return
            if not registered:
                if (path / ".obsidian").is_dir():
                    source = t("Carpeta de Obsidian (.obsidian)")
                elif ((path / "00_Sistema/MANUAL_VAULT.md").is_file()
                      and (path / "99_Recursos").is_dir()):
                    source = t("Estructura de Second Brain")
                else:
                    return
            key = str(path)
            if key not in found:
                found[key] = {"path": key, "name": path.name, "source": source}
        except (OSError, RuntimeError, ValueError):
            pass

    for registry in dict.fromkeys(registry_paths):
        try:
            if registry.stat().st_size > 1_000_000:
                continue
            data = json.loads(registry.read_text(encoding="utf-8"))
            vaults = data.get("vaults", {}) if isinstance(data, dict) else {}
            if not isinstance(vaults, dict):
                continue
            for item in list(vaults.values())[:100]:
                if isinstance(item, dict) and isinstance(item.get("path"), str):
                    add(item["path"], t("Registrado en Obsidian"), registered=True)
        except (OSError, ValueError, UnicodeError):
            continue

    # Search home children and at most two levels of common parent folders.
    # Limits also cover large cloud drives and unreadable directories.
    common = {"Documents", "Documentos", "Desktop", "Escritorio", "Notes", "Notas",
              "Obsidian", "Vaults", "Dropbox", "OneDrive", "Nextcloud", "Projects", "Work"}
    queue = deque([(home, 0)])
    entries_left, directories_left = 4000, 200
    visited = set()
    while queue and entries_left > 0 and directories_left > 0:
        parent, depth = queue.popleft()
        try:
            resolved = parent.resolve()
            if resolved in visited:
                continue
            visited.add(resolved)
            directories_left -= 1
            with os.scandir(parent) as entries:
                for entry in entries:
                    entries_left -= 1
                    if entries_left < 0:
                        break
                    if entry.name.startswith(".") or entry.name in ("node_modules", "vendor", "dist", "target"):
                        continue
                    try:
                        if not entry.is_dir():
                            continue
                        candidate = Path(entry.path)
                        add(candidate, "")
                        # Do not descend into vaults or symlinks.
                        if str(candidate.resolve()) in found or entry.is_symlink():
                            continue
                        if (depth == 0 and entry.name in common) or 0 < depth < 2:
                            queue.append((candidate, depth + 1))
                    except OSError:
                        continue
        except (OSError, RuntimeError):
            continue
    return sorted(found.values(), key=lambda v: (v["name"].casefold(), v["path"]))

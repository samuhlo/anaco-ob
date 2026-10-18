"""Vault profile: the conventions of one Obsidian vault as data.

Destinations, note types, file names, frontmatter, attachments, relation roots
and instruction documents come from a JSON file stored inside the vault, so the
rules travel with it. Notes that already exist are never rewritten.
"""
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path, PurePosixPath
from core import UserError, clean, safe_path, slug

SCHEMA = "anaco-profile/1"
SOURCES = {"type", "constant", "folder_map", "path_segment", "tags", "context", "title", "created", "today",
           "url", "author", "source_format", "assisted", "model", "relations"}
TOKENS = {"date": r"\d{4}-\d{2}-\d{2}", "slug_": r"[a-z0-9_]+", "slug-": r"[a-z0-9-]+",
          "title": r"[^/\\:*?\"<>|#^\[\]]+", "variant": r"(?:_(?:frase|imagen)_[a-f0-9]{6})?"}
FORBIDDEN = re.compile(r'[\\/:*?"<>|#^\[\]]')
SECTIONS = {"summary": "Resumen", "intent": "Intención personal", "quote": "Cita", "quote_context": "Contexto de la cita",
            "relations": "Notas relacionadas", "resources": "Recursos de la fuente", "source": "Fuente", "warning": "Alcance de la captura"}
NOT_FOUND = "Este vault no tiene perfil de Anaco. Abre Opciones → Perfil del vault para escanearlo y confirmar sus reglas."


def relative(vault, value, what):
    """A vault-relative path without hidden parts or escapes."""
    value = clean(value, 500).strip().strip("/")
    parts = PurePosixPath(value).parts
    if not value or any(p.startswith(".") for p in parts):
        raise UserError(f"Perfil del vault: {what} no es una ruta válida dentro del vault.")
    safe_path(vault, value)
    return value


def matches(pattern, folder):
    """Glob over path segments: * is one segment, ** any number (zero included)."""
    def walk(p, f):
        if not p:
            return not f
        if p[0] == "**":
            return any(walk(p[1:], f[i:]) for i in range(len(f) + 1))
        return bool(f) and (p[0] == "*" or p[0] == f[0]) and walk(p[1:], f[1:])
    return walk(pattern.split("/"), folder.split("/") if folder else [])


def title_name(title):
    value = re.sub(r"\s+", " ", FORBIDDEN.sub(" ", clean(title, 300))).strip().lstrip(".")
    return value[:120].strip() or "Captura"


def segment(value):
    return re.sub(r"^\d+_", "", value).replace("_", " ")


class Profile:
    def __init__(self, vault, data, path):
        self.vault, self.path = vault, path
        self.data = validate(vault, data)

    # =========================================================================
    # [CORE] DESTINATIONS AND TYPES
    # =========================================================================

    def destinations(self):
        found = set()
        for directory, dirs, _ in os.walk(self.vault, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not (Path(directory) / d).is_symlink())
            rel = Path(directory).relative_to(self.vault).as_posix()
            if rel != "." and self.rule(rel, required=False):
                found.add(rel)
        return sorted(found)

    def rule(self, folder, required=True):
        for rule in self.data["destinations"]:
            if matches(rule["pattern"], folder):
                return rule
        if required:
            raise UserError("El destino no existe o no respeta la estructura del vault.")
        return None

    def types_for(self, folder):
        return list(self.rule(folder)["types"])

    def default_type(self, folder, derived=False):
        return self.rule(folder)["derived" if derived else "default"]

    def note_type(self, folder, value=None, derived=False):
        value = value or self.default_type(folder, derived)
        if value not in self.types_for(folder):
            raise UserError("El tipo de nota no encaja con el destino. Revisa el tipo y la carpeta.")
        return value

    def study(self, folder):
        return bool(self.rule(folder).get("study"))

    def default_destination(self, folders):
        preferred = self.data.get("default_destination")
        return preferred if preferred in folders else folders[0]

    def separator(self, folder, kind):
        pattern = self.pattern(folder, kind)
        return "-" if "{slug-}" in pattern else " " if "{title}" in pattern else "_"

    def labels(self):
        return {key: value["label"] for key, value in self.data["types"].items()}

    # =========================================================================
    # [CORE] FILE NAMES
    # =========================================================================

    def pattern(self, folder, kind):
        rule = self.rule(folder)
        return rule.get("filenames", {}).get(kind) or self.data["types"][kind]["filename"]

    def patterns(self, folder):
        return {kind: self.pattern(folder, kind) for kind in self.types_for(folder)}

    def filename(self, capture, title, folder, kind=None):
        kind = self.note_type(folder, kind)
        variant = ""
        if capture.get("kind") in ("quote", "image"):
            variant = "_" + ("frase" if capture["kind"] == "quote" else "imagen") + "_" + capture.get("source_fingerprint", capture["fingerprint"])[:6]
        values = {"date": capture["created"][:10], "slug_": slug(title), "slug-": slug(title, "-"), "title": title_name(title), "type": kind, "variant": variant}
        return re.sub(r"\{(date|slug_|slug-|title|type|variant)\}", lambda m: values[m.group(1)], self.pattern(folder, kind))

    def validate_filename(self, name, kind, folder):
        pattern = self.pattern(folder, kind)
        regex = "".join(TOKENS.get(m.group(1), re.escape(kind)) if m.group(1) else re.escape(m.group(0))
                        for m in re.finditer(r"\{(\w[\w-]*)\}|.", pattern, re.S))
        if not re.fullmatch(regex, name or "") or name.startswith(".") or len(name) > 200:
            raise UserError("El nombre del archivo no corresponde al tipo de nota y destino elegidos.")

    # =========================================================================
    # [DATA] FRONTMATTER
    # Context keys: type, folder, tags, context, title, created, today, url,
    # author, source_format, assisted, model and relations as (path, title).
    # =========================================================================

    def frontmatter(self, context):
        out = {}
        for spec in self.data["frontmatter"]:
            if spec["key"] in out or not self.applies(spec.get("when", {}), context):
                continue
            value = self.value(spec, context)
            if value in (None, "", []) and not spec.get("keep_empty"):
                continue
            out[spec["key"]] = value
        return out

    def applies(self, when, context):
        folder = context.get("folder", "") + "/"
        if "types" in when and context.get("type") not in when["types"]:
            return False
        if "folders" in when and not any(folder.startswith(p.rstrip("/") + "/") for p in when["folders"]):
            return False
        if "not_folders" in when and any(folder.startswith(p.rstrip("/") + "/") for p in when["not_folders"]):
            return False
        return not ("assisted" in when and bool(context.get("assisted")) != when["assisted"])

    def value(self, spec, context):
        kind, year = spec["from"], (context.get("today") or context.get("created") or "")[:4]
        if kind == "constant":
            return spec["value"]
        if kind == "folder_map":
            folder = context["folder"] + "/"
            keys = sorted((k for k in spec["values"] if folder.startswith(k.rstrip("/") + "/")), key=len, reverse=True)
            return spec["values"][keys[0]] if keys else None
        if kind == "path_segment":
            parts = context["folder"].split("/")
            return segment(parts[spec["index"]]) if spec["index"] < len(parts) else None
        if kind == "tags":
            expand = lambda values: [v.replace("{year}", year) for v in values]
            return list(dict.fromkeys(expand(spec.get("prepend", [])) + list(context.get("tags") or []) + expand(spec.get("append", []))))
        if kind == "relations":
            return ["[[" + path.removesuffix(".md") + "|" + re.sub(r"[\[\]|]", "", title) + "]]" for path, title in context.get("relations") or []]
        if kind == "assisted":
            return bool(context.get("assisted"))
        if kind == "url":
            url = context.get("url") or ""
            return url if url.startswith(("http://", "https://")) else None
        if kind == "type":
            return context.get("type")
        return context.get({"context": "context", "title": "title", "created": "created", "today": "today", "author": "author",
                            "source_format": "source_format", "model": "model"}[kind])

    # =========================================================================
    # [DATA] RESOURCES
    # =========================================================================

    @property
    def attachments(self):
        return self.data["attachments"]

    @property
    def relation_roots(self):
        return list(self.data["relation_roots"])

    def instructions(self):
        """Readable instruction documents; missing ones are reported, not fatal."""
        found, missing = {}, []
        for rel in self.data["instructions"]:
            path = safe_path(self.vault, rel)
            if path.is_file() and path.stat().st_size <= 1_000_000:
                found[rel] = path.read_text(encoding="utf-8", errors="replace")[:22000]
            else:
                missing.append(rel)
        return found, missing

    # =========================================================================
    # [CORE] CHANGES SINCE CONFIRMATION
    # =========================================================================

    def problems(self):
        """What changed in the vault since the profile was confirmed."""
        out, recorded = [], self.data.get("fingerprint", {}).get("instructions", {})
        for rel in self.data["instructions"]:
            path = safe_path(self.vault, rel)
            if not path.is_file():
                out.append(f"El documento {rel} ya no existe: puede haberse movido. Revisa el perfil.")
            elif recorded.get(rel) and recorded[rel] != digest(path):
                out.append(f"El documento {rel} ha cambiado desde que confirmaste el perfil.")
        destinations = self.destinations()
        for rule in self.data["destinations"]:
            if not any(matches(rule["pattern"], folder) for folder in destinations):
                out.append(f"El destino {rule['pattern']} no tiene ninguna carpeta en el vault.")
        return out

    def section(self, key):
        return self.data["sections"].get(key) or SECTIONS[key]


def validate(vault, data):
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise UserError("Perfil del vault: formato desconocido. Vuelve a escanear el vault en Opciones.")
    types = data.get("types")
    if not isinstance(types, dict) or not types or len(types) > 60:
        raise UserError("Perfil del vault: faltan los tipos de nota.")
    for key, value in types.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,40}", key) or not isinstance(value, dict):
            raise UserError(f"Perfil del vault: tipo de nota no válido ({key}).")
        check_pattern(value.get("filename"), key)
        value["label"] = clean(value.get("label") or key, 80)
    rules = data.get("destinations")
    if not isinstance(rules, list) or not rules or len(rules) > 200:
        raise UserError("Perfil del vault: faltan las carpetas de destino.")
    for rule in rules:
        if not isinstance(rule, dict) or not isinstance(rule.get("pattern"), str) or not rule["pattern"].strip():
            raise UserError("Perfil del vault: hay un destino sin carpeta.")
        if any(p.startswith(".") or p == "" for p in rule["pattern"].split("/")) and rule["pattern"] != "**":
            raise UserError("Perfil del vault: un destino apunta a una carpeta oculta o vacía.")
        chosen = rule.get("types")
        if not isinstance(chosen, list) or not chosen or any(t not in types for t in chosen):
            raise UserError(f"Perfil del vault: el destino {rule['pattern']} usa tipos que no existen.")
        for key in ("default", "derived"):
            rule[key] = rule.get(key) or chosen[0]
            if rule[key] not in chosen:
                raise UserError(f"Perfil del vault: el tipo predeterminado de {rule['pattern']} no está entre sus tipos.")
        for kind, pattern in (rule.get("filenames") or {}).items():
            if kind not in chosen:
                raise UserError(f"Perfil del vault: {rule['pattern']} define nombres para un tipo que no admite.")
            check_pattern(pattern, kind)
    fields = data.get("frontmatter")
    if not isinstance(fields, list) or len(fields) > 60:
        raise UserError("Perfil del vault: el frontmatter no es una lista.")
    for spec in fields:
        if not isinstance(spec, dict) or not re.fullmatch(r"[A-Za-z_][\w-]{0,60}", str(spec.get("key", ""))) or spec.get("from") not in SOURCES:
            raise UserError("Perfil del vault: hay un campo de frontmatter sin nombre válido u origen conocido.")
        if spec["from"] == "folder_map" and not isinstance(spec.get("values"), dict):
            raise UserError(f"Perfil del vault: {spec['key']} necesita valores por carpeta.")
        if spec["from"] == "path_segment" and type(spec.get("index")) is not int:
            raise UserError(f"Perfil del vault: {spec['key']} necesita la posición de la carpeta.")
    data["attachments"] = relative(vault, data.get("attachments"), "la carpeta de adjuntos")
    data["relation_roots"] = [relative(vault, v, "una carpeta de relaciones") for v in data.get("relation_roots") or []]
    data["instructions"] = [relative(vault, v, "un documento de instrucciones") for v in data.get("instructions") or []][:20]
    if data.get("default_destination") is not None:
        data["default_destination"] = relative(vault, data["default_destination"], "el destino predeterminado")
    sections = data.get("sections") or {}
    data["sections"] = {k: clean(v, 120).replace("\n", " ") for k, v in sections.items() if k in SECTIONS and isinstance(v, str)}
    return data


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_pattern(pattern, kind):
    if not isinstance(pattern, str) or not pattern.endswith(".md") or "/" in pattern or "\\" in pattern or pattern.startswith("."):
        raise UserError(f"Perfil del vault: el nombre de archivo de {kind} no es válido.")
    unknown = set(re.findall(r"\{([^}]*)\}", pattern)) - set(TOKENS) - {"type"}
    if unknown or not re.search(r"\{(slug_|slug-|title)\}", pattern):
        raise UserError(f"Perfil del vault: el nombre de archivo de {kind} necesita el título y solo admite {{date}}, {{slug_}}, {{slug-}}, {{title}}, {{type}} y {{variant}}.")


# =============================================================================
# [FLOW] LOCATE AND STORE
# =============================================================================

def locate(app):
    """The configured profile, or the single synced anaco/perfil.json."""
    vault = app.vault()
    configured = app.config().get("profile_path")
    if configured:
        path = safe_path(vault, configured)
        if path.is_file():
            return configured
    found = []
    for directory, dirs, files in os.walk(vault, followlinks=False):
        depth = len(Path(directory).relative_to(vault).parts)
        dirs[:] = [d for d in dirs if not d.startswith(".")] if depth < 4 else []
        if Path(directory).name == "anaco" and "perfil.json" in files:
            found.append((Path(directory) / "perfil.json").relative_to(vault).as_posix())
    return found[0] if len(found) == 1 else None


def load(app):
    rel = locate(app)
    if not rel:
        raise UserError(NOT_FOUND)
    vault = app.vault()
    try:
        data = json.loads(safe_path(vault, rel).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise UserError("Perfil del vault ilegible: " + rel + ". Corrígelo o vuelve a escanear en Opciones.") from exc
    return Profile(vault, data, rel)


def install(app, data, rel):
    """Validate, then write the profile and remember where it lives."""
    vault = app.vault()
    rel = relative(vault, rel, "la ruta del perfil")
    if not rel.endswith(".json"):
        raise UserError("El perfil del vault se guarda como archivo .json.")
    profile = Profile(vault, json.loads(json.dumps(data)), rel)
    profile.data["fingerprint"] = {"instructions": {doc: digest(safe_path(vault, doc)) for doc in profile.data["instructions"] if safe_path(vault, doc).is_file()}}
    # A new vault receives the folders the confirmed profile asked to create.
    for rule in profile.data["destinations"]:
        if rule.get("create") and not any(ch in rule["pattern"] for ch in "*?"):
            safe_path(vault, rule["pattern"]).mkdir(parents=True, exist_ok=True)
    path = safe_path(vault, rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp")
    tmp.write_text(json.dumps(profile.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    cfg = app.config()
    cfg["profile_path"] = rel
    from core import json_dump
    json_dump(app.state / "config.json", cfg)
    return profile

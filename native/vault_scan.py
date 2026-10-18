"""Vault scan: facts about a vault and a deterministic profile proposal.

Only file names, folders and frontmatter are read; note bodies never enter the
facts. Free-text frontmatter is counted, not copied. Instruction documents and
templates are listed by path so the user can choose what the model may read.
"""
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from core import UserError
from vault_profile import SCHEMA, segment

MAX_NOTES = 20000
ROLE_NAMES = {
    "archive": re.compile(r"archiv|legacy|old|antiguo", re.I),
    "templates": re.compile(r"^(templates?|plantillas?)$", re.I),
    "attachments": re.compile(r"^(adjuntos|attachments|assets|media|archivos_adjuntos)$", re.I),
    "daily": re.compile(r"diario|daily|journal|bitacora", re.I),
    "system": re.compile(r"sistema|system|^meta$|config", re.I),
}
INSTRUCTION_TYPES = {"guia", "guide", "manual", "instrucciones", "instrucciones_agente", "instructions"}
INSTRUCTION_NAMES = re.compile(r"^(AGENTS|CLAUDE|GEMINI|SKILL|README)\.md$|MANUAL|^guia_|^instrucciones", re.I)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")
TYPE_KEYS = ("tipo", "type", "categoria", "category")
INDEX_TYPES = {"indice", "index", "moc", "hub"}


def frontmatter(text):
    """Minimal YAML frontmatter: scalars, inline lists and dash lists."""
    match = re.match(r"---\r?\n(.*?)\r?\n---", text, re.S)
    if not match:
        return {}
    out, current = {}, None
    for line in match.group(1).splitlines():
        item = re.match(r"\s+-\s*(.*)$", line)
        if item and current:
            out.setdefault(current, [])
            if isinstance(out[current], list):
                out[current].append(item.group(1).strip().strip("'\""))
            continue
        pair = re.match(r"([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not pair:
            continue
        current, raw = pair.group(1), pair.group(2).strip()
        if raw.startswith("["):
            try:
                value = json.loads(raw)
            except ValueError:
                value = [v.strip().strip("'\"") for v in raw.strip("[]").split(",") if v.strip()]
        elif raw == "":
            value = []
        else:
            value = raw.strip("'\"")
        out[current] = value
    return out


def shape(stem, kind):
    """Generalize a file name into a profile pattern."""
    if kind and re.fullmatch(re.escape(kind) + r"_\d{4}-\d{2}-\d{2}_[a-z0-9-]+", stem):
        return "{type}_{date}_{slug-}"
    match = re.fullmatch(r"([a-z]+)_\d{4}-\d{2}-\d{2}_[a-z0-9_]+", stem)
    if match:
        return match.group(1) + "_{date}_{slug_}"
    match = re.fullmatch(r"([a-z]+)_[a-z0-9_]+", stem)
    if match:
        return match.group(1) + "_{slug_}"
    if re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)+", stem):
        return "{slug-}"
    return "{title}"


# =============================================================================
# [DATA] FACTS
# =============================================================================

def scan(app):
    vault = app.vault()
    notes, folders, documents = [], defaultdict(lambda: {"notes": 0, "images": 0}), []
    for directory, dirs, files in os.walk(vault, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not (Path(directory) / d).is_symlink())
        rel = Path(directory).relative_to(vault).as_posix()
        rel = "" if rel == "." else rel
        folders[rel]
        for name in sorted(files):
            path = Path(directory) / name
            if path.is_symlink():
                continue
            if name.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".pdf", ".mp4")):
                folders[rel]["images"] += 1
            if not name.endswith(".md") or len(notes) >= MAX_NOTES:
                continue
            try:
                with path.open(encoding="utf-8", errors="replace") as stream:
                    head = stream.read(16000)
            except OSError:
                continue
            fields = frontmatter(head)
            notes.append({"folder": rel, "name": name, "fields": fields, "size": path.stat().st_size})
            folders[rel]["notes"] += 1
    for folder in list(folders):
        parent = folder
        while "/" in parent:
            parent = parent.rsplit("/", 1)[0]
            folders[parent]["nested_images"] = folders[parent].get("nested_images", 0) + folders[folder]["images"]
    roles = detect_roles(vault, folders)
    for item in notes:
        doc = document_kind(item, roles)
        if doc:
            documents.append({"path": join(item["folder"], item["name"]), "kind": doc, "size": item["size"],
                              "type": scalar(item["fields"], TYPE_KEYS)})
    suggest(vault, documents)
    excluded = excluded_folders(roles, [d for d in documents if d["suggested"]], notes)
    usable = [n for n in notes if n["folder"] and not inside(n["folder"], excluded)]
    return {"notes": len(notes), "folders": {k: v for k, v in sorted(folders.items()) if k}, "roles": roles,
            "documents": documents, "excluded": sorted(excluded), "stats": statistics(usable)}


def join(folder, name):
    return f"{folder}/{name}" if folder else name


def inside(folder, prefixes):
    return any(folder == p or folder.startswith(p + "/") for p in prefixes)


def scalar(fields, keys):
    for key in keys:
        if isinstance(fields.get(key), str) and fields[key]:
            return fields[key]
    return ""


def detect_roles(vault, folders):
    config = lambda name: _json(vault / ".obsidian" / f"{name}.json")
    roles = {"templates": config("templates").get("folder", "").strip("/"), "daily": config("daily-notes").get("folder", "").strip("/"),
             "attachments": (config("app").get("attachmentFolderPath") or "").strip("/").removeprefix("./"), "archive": [], "system": []}
    archive = [f for f in folders if f and "/" not in f and ROLE_NAMES["archive"].search(f)]
    for folder, info in sorted(folders.items(), key=lambda kv: kv[0].count("/")):
        if not folder or inside(folder, archive):
            continue
        name = folder.split("/")[-1]
        if not roles["templates"] and ROLE_NAMES["templates"].search(name):
            roles["templates"] = folder
        if not roles["attachments"] and ROLE_NAMES["attachments"].search(name) and info["images"] + info.get("nested_images", 0):
            roles["attachments"] = folder
        if not roles["daily"] and "/" not in folder and ROLE_NAMES["daily"].search(name):
            roles["daily"] = folder
        if "/" not in folder and ROLE_NAMES["system"].search(name):
            roles["system"].append(folder)
    roles["archive"] = archive
    return roles


def _json(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def document_kind(item, roles):
    folder, name = item["folder"], item["name"]
    if inside(folder, roles["archive"]):
        return None
    if roles["templates"] and inside(folder, [roles["templates"]]):
        return "template"
    if name == "SKILL.md":
        return "skill"
    if not folder and re.fullmatch(r"(AGENTS|CLAUDE|GEMINI)\.md", name):
        return "instructions"
    kind = scalar(item["fields"], TYPE_KEYS)
    if kind in INSTRUCTION_TYPES or INSTRUCTION_NAMES.search(name):
        return "guide"
    return None


def suggest(vault, documents):
    """Vault instructions: agent files, skills, what they link and their neighbours."""
    by_path = {d["path"]: d for d in documents}
    entry = [d for d in documents if d["kind"] in ("instructions", "skill")]
    linked = set()
    for doc in entry:
        try:
            text = (vault / doc["path"]).read_text(encoding="utf-8", errors="replace")[:60000]
        except OSError:
            continue
        base = doc["path"].rsplit("/", 1)[0] if "/" in doc["path"] else ""
        for target in re.findall(r"\]\(([^)#\s]+\.md)\)", text) + [t + ("" if t.endswith(".md") else ".md") for t in re.findall(r"\[\[([^\]|#]+)", text)]:
            target = target.lstrip("./")
            for candidate in (target, f"{base}/{target}" if base else target):
                if candidate in by_path:
                    linked.add(candidate)
            linked.update(p for p in by_path if p.endswith("/" + target.split("/")[-1]))
    folders = {p.rsplit("/", 1)[0] for p in linked if "/" in p}
    named = bool(entry)
    for doc in documents:
        folder = doc["path"].rsplit("/", 1)[0] if "/" in doc["path"] else ""
        if doc["kind"] in ("instructions", "skill") or doc["path"] in linked:
            doc["suggested"] = True
        elif doc["kind"] == "guide":
            # Without agent files, a MANUAL is the only reliable signal.
            doc["suggested"] = folder in folders if named else bool(re.search(r"MANUAL", doc["path"]))
        else:
            doc["suggested"] = doc["kind"] == "template"


def excluded_folders(roles, documents, notes):
    excluded = set(roles["archive"]) | set(roles["system"])
    for key in ("templates", "attachments", "daily"):
        if roles[key]:
            excluded.add(roles[key])
    # Folders that mostly hold instructions are documentation, not destinations.
    docs = Counter(d["path"].rsplit("/", 1)[0] for d in documents if "/" in d["path"])
    total = Counter(n["folder"] for n in notes)
    excluded |= {folder for folder, count in docs.items() if count * 2 >= total[folder]}
    return excluded


def statistics(notes):
    """Per folder: note count, type values, name shapes and frontmatter keys.
    Values are kept only when categorical; free text is reduced to a count."""
    per = defaultdict(lambda: {"count": 0, "types": Counter(), "shapes": defaultdict(Counter), "keys": defaultdict(Counter), "order": defaultdict(list), "typed": defaultdict(Counter)})
    for n in notes:
        info, fields = per[n["folder"]], n["fields"]
        kind = scalar(fields, TYPE_KEYS)
        info["count"] += 1
        info["types"][kind] += 1
        info["shapes"][kind][shape(n["name"][:-3], kind)] += 1
        for position, (key, value) in enumerate(fields.items()):
            info["order"][key].append(position)
            info["keys"][key][describe(value, n["folder"])] += 1
            info["typed"][kind][key] += 1
    out = {}
    for folder, info in per.items():
        keys = {}
        for key, values in info["keys"].items():
            categorical = len(values) <= 12 and all(len(v) <= 80 for v in values)
            keys[key] = {"count": sum(values.values()), "position": sum(info["order"][key]) / len(info["order"][key]),
                         "values": dict(values.most_common(12)) if categorical else {"(texto libre)": sum(values.values())}}
        out[folder] = {"count": info["count"], "types": dict(info["types"]), "shapes": {k: dict(v) for k, v in info["shapes"].items()}, "keys": keys,
                       "typed_keys": {k: dict(v) for k, v in info["typed"].items()}}
    return out


def describe(value, folder):
    """A short, comparable description of one frontmatter value."""
    if isinstance(value, list):
        if not value:
            return "(lista vacía)"
        return "(enlaces)" if all(str(v).startswith("[[") for v in value) else "(lista)"
    value = str(value)
    if DATE.match(value):
        return "(fecha)"
    parts = folder.split("/")
    for index, part in enumerate(parts):
        if value == segment(part):
            return f"(carpeta {index})"
    return value


# =============================================================================
# [FLOW] DETERMINISTIC PROPOSAL
# =============================================================================

def propose(facts):
    stats, evidence = facts["stats"], {}
    # A folder holding only index notes is navigation, not a place for captures.
    destinations = sorted((f for f, info in stats.items() if set(info["types"]) - INDEX_TYPES), key=lambda f: (-stats[f]["count"], f))
    typed = sum(info["types"].get("", 0) != info["count"] for info in stats.values())
    if not destinations:
        rules = [{"pattern": "Anaco", "types": ["nota"], "default": "nota", "derived": "nota", "create": True}]
        types = {"nota": {"label": "Nota", "filename": "{title}.md"}}
        evidence["destinations"] = "El vault no tiene notas: se creará la carpeta Anaco al confirmar."
        return finish(facts, types, rules, generic_fields(), evidence, "Anaco")
    types, rules = {}, []
    all_shapes = defaultdict(Counter)
    for folder in sorted(destinations):
        info = stats[folder]
        for kind, shapes in info["shapes"].items():
            all_shapes[kind or "nota"].update(shapes)
    for kind, shapes in all_shapes.items():
        best, count = shapes.most_common(1)[0]
        total = sum(shapes.values())
        pattern = best + ".md" if count * 10 >= total * 6 and count >= 2 else "{title}.md"
        types[kind] = {"label": kind.replace("_", " ").capitalize(), "filename": pattern}
        evidence[f"filename:{kind}"] = f"{count} de {total} notas de tipo {kind} se llaman como {best}" if pattern != "{title}.md" else f"Las notas de tipo {kind} no siguen un patrón común: se usará el título"
    for folder in sorted(destinations):
        info = stats[folder]
        ranked = [k or "nota" for k, _ in sorted(Counter(info["types"]).items(), key=lambda kv: (kv[0] in INDEX_TYPES, -kv[1], kv[0]))]
        default = ranked[0]
        rules.append({"pattern": folder, "types": ranked, "default": default, "derived": ranked[1] if len(ranked) > 1 and default.startswith("fuente") else default})
        evidence[f"destination:{folder}"] = f"{info['count']} notas; tipos: " + ", ".join(f"{k or 'nota'} ({v})" for k, v in Counter(info["types"]).most_common(5))
    fields = typed_fields(stats, destinations, evidence) if typed else generic_fields()
    if not typed:
        evidence["frontmatter"] = "Las notas no tienen un tipo en el frontmatter: se usará un frontmatter mínimo."
    return finish(facts, types, rules, fields, evidence, destinations[0])


def generic_fields():
    return [{"key": "tags", "from": "tags", "keep_empty": True}, {"key": "fuente_url", "from": "url"},
            {"key": "fuente_autor", "from": "author"}, {"key": "creado", "from": "created"}]


SEMANTIC = [
    (re.compile(r"^(tags|etiquetas)$"), {"from": "tags", "keep_empty": True}),
    (re.compile(r"relac|related|links|enlaces"), {"from": "relations", "keep_empty": True}),
    (re.compile(r"^(fuente_url|url|source_url|source|link)$"), {"from": "url"}),
    (re.compile(r"^(fuente_autor|autor|author)$"), {"from": "author"}),
    (re.compile(r"^(formato|format)$"), {"from": "source_format"}),
    (re.compile(r"^(contexto|context|descripcion|description|resumen)$"), {"from": "context"}),
    (re.compile(r"llm_asistido|ai_assisted"), {"from": "assisted"}),
    (re.compile(r"llm_modelo|ai_model"), {"from": "model", "when": {"assisted": True}}),
    (re.compile(r"llm_modific|ai_updated"), {"from": "today", "when": {"assisted": True}}),
    (re.compile(r"creado|created|creation"), {"from": "created"}),
    (re.compile(r"modific|updated|actualiz"), {"from": "today"}),
]


def typed_fields(stats, destinations, evidence):
    total = sum(stats[f]["count"] for f in destinations)
    keys = defaultdict(lambda: {"count": 0, "position": 0.0, "folders": {}})
    for folder in destinations:
        for key, info in stats[folder]["keys"].items():
            entry = keys[key]
            entry["count"] += info["count"]
            entry["position"] += info["position"] * info["count"]
            entry["folders"][folder] = info
    fields = []
    for key, entry in sorted(keys.items(), key=lambda kv: kv[1]["position"] / kv[1]["count"]):
        share = entry["count"] / total
        spec = field_for(key, entry, stats, destinations)
        if not spec:
            continue
        if share < 0.5 and "when" not in spec and spec["from"] not in ("folder_map", "path_segment"):
            continue
        fields.append({"key": key, **spec})
        evidence[f"field:{key}"] = f"{entry['count']} de {total} notas en destinos usan {key}" + (f" ({spec['from']})" if spec["from"] != "constant" else "")
    return fields


def field_for(key, entry, stats, destinations):
    if key in TYPE_KEYS:
        return {"from": "type"}
    values = Counter()
    for info in entry["folders"].values():
        values.update(info["values"])
    if any(v.startswith("(carpeta ") for v in values) and len(values) == 1:
        return {"from": "path_segment", "index": int(next(iter(values))[9:-1])}
    for pattern, spec in SEMANTIC:
        if pattern.search(key):
            spec = dict(spec)
            limited = types_where_present(key, stats, destinations)
            if limited and spec["from"] in ("url", "author", "source_format"):
                spec["when"] = {"types": limited}
            return spec
    # Categorical and constant inside each folder: a value per folder, shortened to common prefixes.
    mapping = {}
    for folder, info in entry["folders"].items():
        options = {v: c for v, c in info["values"].items() if not v.startswith("(")}
        if len(options) != 1 or sum(options.values()) * 10 < stats[folder]["count"] * 9:
            continue
        mapping[folder] = next(iter(options))
    covered = sum(stats[f]["count"] for f in mapping)
    if not mapping or (len(mapping) < 2 and covered * 10 < sum(stats[f]["count"] for f in destinations) * 3):
        return None
    if len(set(mapping.values())) == 1 and len(mapping) == len(destinations):
        return {"from": "constant", "value": next(iter(mapping.values()))}
    return {"from": "folder_map", "values": compress(mapping, destinations)}


def types_where_present(key, stats, destinations):
    """Types whose notes carry the key at least half of the time."""
    present, totals = Counter(), Counter()
    for folder in destinations:
        for kind, keys in stats[folder]["typed_keys"].items():
            totals[kind or "nota"] += stats[folder]["types"].get(kind, 0)
            present[kind or "nota"] += keys.get(key, 0)
    limited = sorted(kind for kind, count in present.items() if count * 2 >= totals[kind] and totals[kind])
    return limited if limited and len(limited) < len(totals) else []


def compress(mapping, destinations):
    """Use the shortest folder prefix whose destinations all share a value."""
    out = {}
    for folder, value in sorted(mapping.items()):
        parts = folder.split("/")
        for depth in range(1, len(parts) + 1):
            prefix = "/".join(parts[:depth])
            group = [f for f in destinations if f == prefix or f.startswith(prefix + "/")]
            if all(mapping.get(f) == value for f in group):
                out[prefix] = value
                break
    return out


def finish(facts, types, rules, fields, evidence, default):
    roles = facts["roles"]
    attachments = (roles["attachments"] + "/anaco") if roles["attachments"] else "Anaco/adjuntos" if default == "Anaco" else "adjuntos/anaco"
    tops = sorted({r["pattern"].split("/")[0] for r in rules})
    documents = [d["path"] for d in facts["documents"] if d["suggested"] and d["kind"] != "template"]
    documents += [d["path"] for d in facts["documents"] if d["suggested"] and d["kind"] == "template" and d["type"] in types]
    for item in facts["documents"]:
        evidence.setdefault("documents", "")
    evidence["documents"] = f"{len(facts['documents'])} documentos de instrucciones y plantillas encontrados"
    evidence["attachments"] = f"Carpeta de adjuntos detectada: {roles['attachments']}" if roles["attachments"] else "No hay carpeta de adjuntos: se propone una nueva"
    profile = {"schema": SCHEMA, "types": types, "destinations": rules, "frontmatter": fields, "attachments": attachments,
               "relation_roots": tops if tops != ["Anaco"] else [], "instructions": documents[:20], "sections": {}, "default_destination": default}
    return {"profile": profile, "evidence": evidence, "excluded": facts["excluded"], "documents": facts["documents"]}

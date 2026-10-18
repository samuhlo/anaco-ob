"""Embedded resources of a web article: posts, CodePen demos and silent clips.

The captured text keeps a {{recurso:N}} token where each one appeared. Rendering
replaces the tokens of selected resources and keeps unplaced ones after the body.
"""
import hashlib
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from core import UserError, clean

TOKEN = re.compile(r"\{\{\s*recurso\s*:\s*(\d{1,3})\s*\}\}")
ASSET = re.compile(r"[a-f0-9]{64}\.(mp4|webm|mov|js|css|html)")
# Names chosen by the browser for files next to index.html; imports point to them.
LIB_NAME = re.compile(r"[a-f0-9]{8}-[A-Za-z0-9._@-]{1,100}\.(js|mjs|css)")
ASSET_TYPES = {".mp4": 100_000_000, ".webm": 100_000_000, ".mov": 100_000_000, ".js": 10_000_000, ".css": 10_000_000, ".html": 5_000_000}
# Loop protection is CodePen runtime code; offline it becomes a no-op.
CP_STUB = '<script>window.CP={shouldStopExecution:function(){return false},exitedLoop:function(){}};</script>'


def asset_dir(app):
    return app.state / "assets"


def store_asset(app, source, suffix):
    """Move a completed upload into content-addressed storage."""
    raw = source.read_bytes()
    name = hashlib.sha256(raw).hexdigest() + suffix
    target = asset_dir(app) / name
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if target.exists():source.unlink()
    else:source.replace(target)
    return {"asset": name, "size": len(raw)}


def read_asset(app, name):
    if not isinstance(name, str) or not ASSET.fullmatch(name):
        raise UserError("Recurso local no válido.")
    path = asset_dir(app) / name
    if not path.is_file():
        raise UserError("Falta un recurso descargado de la captura. Vuelve a capturar la página.")
    return path.read_bytes()


def web_url(value):
    value = clean(value, 2000)
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise UserError("Un recurso incrustado tiene una dirección no válida.")
    return value


# =============================================================================
# [DATA] STAGE
# Validates what the browser sent. Binary content arrives earlier as assets.
# =============================================================================

def stage(app, values):
    if values is None:
        return None
    if not isinstance(values, list) or len(values) > 60:
        raise UserError("Lista de recursos incrustados no válida.")
    result = []
    for value in values:
        if not isinstance(value, dict) or value.get("type") not in ("tweet", "clip", "pen"):
            raise UserError("Tipo de recurso incrustado no admitido.")
        item = {"type": value["type"], "selected": value.get("selected") is True, "url": web_url(value.get("url")),
                "title": clean(value.get("title"), 300)}
        if item["type"] == "tweet":
            item.update(author=clean(value.get("author"), 300), text=clean(value.get("text"), 4000))
        elif item["type"] == "clip":
            item.update(caption=clean(value.get("caption"), 600), name=clean(value.get("name"), 200),
                        duration=value.get("duration") if isinstance(value.get("duration"), (int, float)) else None)
            if item["selected"]:
                raw = read_asset(app, value.get("asset"))
                item.update(asset=value["asset"], size=len(raw))
        else:
            item.update(user=clean(value.get("user"), 80), slug=clean(value.get("slug"), 40))
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", item["user"]) or not re.fullmatch(r"[A-Za-z0-9]{3,20}", item["slug"]):
                raise UserError("Demo de CodePen no válida.")
            code = value.get("code") if isinstance(value.get("code"), dict) else {}
            item["code"] = {k: clean(code.get(k), 120_000) for k in ("html", "css", "js") if code.get(k)}
            item["code_source"] = "compiled" if value.get("code_source") == "compiled" else "source"
            demo = value.get("demo")
            if item["selected"] and isinstance(demo, dict):
                read_asset(app, demo.get("page"))
                libs = demo.get("libs") if isinstance(demo.get("libs"), list) else []
                if len(libs) > 40:
                    raise UserError("La demo depende de demasiados archivos externos.")
                for lib in libs:
                    read_asset(app, lib.get("asset") if isinstance(lib, dict) else None)
                    if lib.get("name") is not None and not LIB_NAME.fullmatch(str(lib["name"])):
                        raise UserError("Nombre de archivo de la demo no válido.")
                item["demo"] = {"page": demo["page"], "libs": [{"url": web_url(lib["url"]), "asset": lib["asset"], **({"name": lib["name"]} if lib.get("name") else {})} for lib in libs]}
        result.append(item)
    return result


def for_prompt(values):
    """What the model needs to place and explain each resource; never binaries."""
    out = []
    for index, item in enumerate(values or []):
        if not item.get("selected"):
            continue
        entry = {"token": "{{recurso:%d}}" % index, "type": item["type"], "title": item.get("title", "")}
        if item["type"] == "tweet":
            entry.update(author=item.get("author", ""), text=item.get("text", ""))
        elif item["type"] == "clip":
            entry.update(caption=item.get("caption", ""), duration=item.get("duration"))
        else:
            entry["code"] = {k: v[:12000] for k, v in item.get("code", {}).items()}
        out.append(entry)
    return out


# =============================================================================
# [FLOW] RENDER
# =============================================================================

def quote(text):
    return "\n".join("> " + line if line else ">" for line in text.split("\n"))


def link(url):
    return url.replace("<", "%3C").replace(">", "%3E").replace("\n", "")


def offline_page(app, demo, folder):
    """Rewrite the compiled CodePen document to load its libraries from the vault."""
    html = read_asset(app, demo["page"]).decode("utf-8", errors="replace")
    files = []
    for lib in demo["libs"]:
        raw = read_asset(app, lib["asset"])
        base = re.sub(r"[^A-Za-z0-9._-]", "_", PurePosixPath(urlsplit(lib["url"]).path).name or "lib.js")[:80]
        name = lib.get("name") or lib["asset"][:12] + "-" + base
        files.append((folder + "/" + name, raw))
        html = html.replace('"' + lib["url"] + '"', '"' + name + '"').replace("'" + lib["url"] + "'", "'" + name + "'")
    html = re.sub(r'<script[^>]+src="https://[^"]*codepen\.io/[^"]*stopExecutionOnTimeout[^"]*"[^>]*>\s*</script>', "", html)
    html = re.sub(r'<link[^>]+href="https://cpwebassets\.codepen\.io/[^"]*"[^>]*>', "", html)
    html = re.sub(r"(<head[^>]*>)", lambda m: m.group(1) + CP_STUB, html, count=1) if "<head" in html else CP_STUB + html
    return html.encode("utf-8"), files


def block(app, item, attachments):
    """Markdown and files for one selected resource."""
    if item["type"] == "tweet":
        lines = ["![](" + link(item["url"]) + ")", "", "> [!quote] " + (item.get("author") or "Publicación en X")]
        if item.get("text"):
            lines.append(quote(item["text"]))
        lines.append("> [Ver en X](<" + link(item["url"]) + ">)")
        return "\n".join(lines), []
    if item["type"] == "clip":
        raw = read_asset(app, item["asset"])
        rel = attachments + "/clips/" + item["asset"]
        caption = item.get("caption") or item.get("title") or ""
        return "![[" + rel + "]]" + ("\n\n*" + caption.replace("*", "") + "*" if caption else ""), [(rel, raw)]
    folder = attachments + "/codepen/" + item["user"] + "-" + item["slug"]
    title = (item.get("title") or "Demo de CodePen").replace("\n", " ")
    parts, files = ["> [!example] Demo · " + title], []
    if item.get("demo"):
        page, files = offline_page(app, item["demo"], folder)
        files = [(folder + "/index.html", page)] + files
        parts.append("> [Ver en CodePen](<" + link(item["url"]) + ">) · [[" + folder + "/index.html|Abrir la demo sin conexión]]")
        parts.append("\n```html-preview\n[[" + folder + "/index.html]]\nheight: 420\n```")
    else:
        parts.append("> [Ver en CodePen](<" + link(item["url"]) + ">) · Sin copia local: la demo necesita conexión.")
    code = item.get("code") or {}
    if code:
        label = "Código de la demo" + (" (compilado por CodePen)" if item.get("code_source") == "compiled" else "")
        body = [f"```{lang}\n{code[key].rstrip()}\n```" for key, lang in (("html", "html"), ("css", "css"), ("js", "js")) if code.get(key)]
        parts.append("\n> [!code]- " + label + "\n" + quote("\n\n".join(body)))
    return "\n".join(parts), files


def apply(app, c, body, attachments, root):
    """Replace tokens in body; the root note also receives unplaced resources."""
    values = c.get("embeds") or []
    assets, used = [], set()

    def replace(match):
        index = int(match.group(1))
        if index >= len(values) or not values[index]["selected"] or index in used:
            return ""
        used.add(index)
        text, files = block(app, values[index], attachments)
        assets.extend(files)
        return text

    body = re.sub(r"\n{3,}", "\n\n", TOKEN.sub(replace, body))
    rest = ""
    if root and values:
        drafts = [c.get("draft", {}).get("body", "")] + [n.get("body", "") for n in c.get("bundle", {}).get("notes", [])]
        placed = {int(m.group(1)) for text in drafts for m in TOKEN.finditer(text)}
        pending = [i for i, item in enumerate(values) if item["selected"] and i not in placed and i not in used]
        sections = []
        for index in pending:
            text, files = block(app, values[index], attachments)
            sections.append(text)
            assets.extend(files)
        if sections:
            rest = "## Recursos de la fuente\n\n" + "\n\n".join(sections)
    return body, rest, assets


def guidance(capture):
    if not any(item.get("selected") for item in capture.get("embeds") or []):
        return ""
    return ("La captura contiene marcadores {{recurso:N}} que representan publicaciones, demos de código y clips de vídeo; su contenido está en capture.embeds. "
            "Coloca cada marcador una sola vez, en una línea propia, en el punto del body donde aporte. No inventes marcadores ni los escribas dentro de bloques de código. "
            "El servicio inserta el recurso real: no copies el código completo de las demos; explica qué muestra cada recurso y qué técnica ilustra. ")

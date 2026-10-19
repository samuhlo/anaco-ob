#!/usr/bin/env python3
"""Interface translations of the extension.

  python3 scripts/i18n.py extract   # one-off: move HTML texts to _locales/es and mark them with data-i18n
  python3 scripts/i18n.py build     # write extension/i18n-catalog.js from extension/_locales
  python3 scripts/i18n.py check     # every key used exists in every language, with the same placeholders

_locales/<lang>/messages.json is the single source; the catalog is generated.
The local service writes its texts in Spanish and translates them with
native/locales/en.json, keyed by the Spanish text; check covers it too.
"""
import ast
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "extension"
LOCALES = EXT / "_locales"
LANGUAGES = ("es", "en")
SKIP = {"code", "pre", "script", "style"}
ATTRIBUTES = ("placeholder", "title", "aria-label", "alt")
BRAND = {"Anaco", "Anac", ""}


def slug(text):
    value = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_")[:40] or "text"


def load(lang):
    path = LOCALES / lang / "messages.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save(lang, messages):
    path = LOCALES / lang / "messages.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(sorted(messages.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Texts(HTMLParser):
    """Text nodes and translatable attributes with their absolute offsets."""

    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source, self.stack, self.found = source, [], []
        self.lines = [0]
        for line in source.splitlines(keepends=True):
            self.lines.append(self.lines[-1] + len(line))

    def position(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        start = self.position()
        end = self.source.index(">", start) + 1
        self.found.append(("tag", tag, start, end, dict(attrs)))
        if tag not in ("input", "img", "br", "meta", "link", "source", "track"):
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass

    def handle_data(self, data):
        if not data.strip() or any(t in SKIP for t in self.stack) or not re.search(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]", data):
            return
        self.found.append(("text", self.stack[-1] if self.stack else "", self.position(), self.position() + len(data), data))


def extract():
    messages, used = load("es"), {}
    for page in ("panel", "options", "review", "welcome"):
        path = EXT / f"{page}.html"
        source = path.read_text(encoding="utf-8")
        parser = Texts(source)
        parser.feed(source)
        edits = []

        def key_for(text):
            text = re.sub(r"\s+", " ", text.strip())
            for existing, value in messages.items():
                if value["message"] == text:
                    return existing
            base = f"{page}_{slug(text)}"
            key, n = base, 2
            while key in messages:
                key, n = f"{base}_{n}", n + 1
            messages[key] = {"message": text}
            return key

        for item in parser.found:
            if item[0] == "tag":
                _, tag, start, end, attrs = item
                tag_source = source[start:end]
                additions = []
                for name in ATTRIBUTES:
                    value = attrs.get(name)
                    if value and value not in BRAND and re.search(r"[A-Za-zÁÉÍÓÚáéíóúñ]{3}", value):
                        additions.append(f' data-i18n-{name}="{key_for(value)}"')
                if tag == "html":
                    continue
                if additions:
                    closing = 2 if tag_source.endswith("/>") else 1
                    edits.append((end - closing, end - closing, "".join(additions)))
                continue
            _, parent, start, end, data = item
            text = data.strip()
            if text in BRAND:
                continue
            key = key_for(text)
            lead, trail = data[: len(data) - len(data.lstrip())], data[len(data.rstrip()):]
            if parent in ("option", "title"):
                # These elements cannot hold a span: mark the element itself.
                open_tag = source.rfind("<" + parent, 0, start)
                close = source.index(">", open_tag)
                edits.append((close, close, f' data-i18n="{key}"'))
            else:
                edits.append((start, end, f'{lead}<span data-i18n="{key}">{text}</span>{trail}'))
        for start, end, replacement in sorted(edits, key=lambda e: e[0], reverse=True):
            source = source[:start] + replacement + source[end:]
        path.write_text(source, encoding="utf-8")
        used[page] = len(edits)
    save("es", messages)
    print("Marcados:", used, "· mensajes:", len(messages))


def build():
    catalog = {lang: {k: v["message"] for k, v in load(lang).items()} for lang in LANGUAGES}
    (EXT / "i18n-catalog.js").write_text("/* Generated by scripts/i18n.py build from extension/_locales. Do not edit. */\n"
                                          "globalThis.AnacoObCatalog=" + json.dumps(catalog, ensure_ascii=False, sort_keys=True) + ";\n", encoding="utf-8")
    print("Catálogo:", {lang: len(v) for lang, v in catalog.items()})


def used_keys():
    keys = set()
    for path in EXT.glob("*.html"):
        keys |= set(re.findall(r'data-i18n(?:-[a-z-]+)?="([a-z0-9_]+)"', path.read_text(encoding="utf-8")))
    for path in EXT.glob("*.js"):
        if path.name == "i18n-catalog.js":
            continue
        keys |= set(re.findall(r"""\btx\(\s*['"]([a-z0-9_]+)['"]""", path.read_text(encoding="utf-8")))
    keys |= set(re.findall(r"__MSG_([a-z0-9_]+)__", (EXT / "manifest.json").read_text(encoding="utf-8")))
    return keys


NATIVE = ROOT / "native"
TRANSLATED = {"UserError": 0, "t": 0, "n": 0}


def native_texts():
    """Spanish texts passed to UserError, t() and n(), and the calls that hide them."""
    texts, problems = {}, []
    for path in sorted(NATIVE.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call) or getattr(node.func, "id", None) not in TRANSLATED or not node.args:
                continue
            first = node.args[0]
            where = f"{path.name}:{node.lineno}"
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                texts.setdefault(first.value, where)
            elif isinstance(first, (ast.JoinedStr, ast.BinOp)):
                # GUARD -> A formatted message has no stable key: pass the values by name instead.
                problems.append(f"{where}: texto formateado; usa una plantilla con valores con nombre")
    return texts, problems


def native_problems():
    texts, problems = native_texts()
    catalog = json.loads((NATIVE / "locales" / "en.json").read_text(encoding="utf-8"))
    for text, where in texts.items():
        if text not in catalog:
            problems.append(f"{where}: falta en native/locales/en.json: {text[:70]}")
        elif sorted(re.findall(r"{(\w+)}", text)) != sorted(re.findall(r"{(\w+)}", catalog[text])):
            problems.append(f"{where}: otros marcadores en inglés: {text[:70]}")
    for text in catalog:
        if text not in texts:
            problems.append(f"native/locales/en.json: sobra {text[:70]}")
    return problems


def check():
    problems = []
    catalogs = {lang: load(lang) for lang in LANGUAGES}
    for key in sorted(used_keys()):
        for lang, messages in catalogs.items():
            if key not in messages:
                problems.append(f"{lang}: falta {key}")
    base = catalogs["es"]
    for lang, messages in catalogs.items():
        for key, value in messages.items():
            if key not in base:
                problems.append(f"{lang}: sobra {key}")
            elif sorted(re.findall(r"\$\d", value["message"])) != sorted(re.findall(r"\$\d", base[key]["message"])):
                problems.append(f"{lang}: {key} usa otros marcadores que es")
    for path in EXT.glob("*.js"):
        if path.name in ("i18n.js", "i18n-catalog.js"):
            continue
        # check only sees literal keys: a computed one could be missing unnoticed.
        for line in re.findall(r"^.*\btx\(\s*[^'\"\s].*$", path.read_text(encoding="utf-8"), re.M):
            problems.append(f"{path.name}: clave no literal en {line.strip()[:80]}")
    generated = {lang: {k: v["message"] for k, v in catalogs[lang].items()} for lang in LANGUAGES}
    catalog = (EXT / "i18n-catalog.js").read_text(encoding="utf-8") if (EXT / "i18n-catalog.js").exists() else ""
    if json.dumps(generated, ensure_ascii=False, sort_keys=True) not in catalog:
        problems.append("i18n-catalog.js no está al día: ejecuta scripts/i18n.py build")
    problems += native_problems()
    for problem in problems:
        print(problem)
    print("Claves usadas:", len(used_keys()), "· problemas:", len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "check"
    sys.exit({"extract": extract, "build": build, "check": check}[command]() or 0)

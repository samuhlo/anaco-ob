"""Texts of the service in the user's languages.

Spanish is the main language: each text is written in Spanish in the code and
that text is its key in locales/en.json. t() follows the interface language of
the current request; n() follows the language chosen for notes.
"""
import json
from pathlib import Path

LANGUAGES = ("es", "en")
CATALOG = json.loads((Path(__file__).with_name("locales") / "en.json").read_text(encoding="utf-8"))
_interface = "es"
_notes = "es"


def set_language(value):
    global _interface
    _interface = value if value in LANGUAGES else "es"


def set_note_language(value):
    global _notes
    _notes = value if value in LANGUAGES else "es"


def note_language():
    return _notes


def _text(language, text, values):
    template = CATALOG.get(text, text) if language == "en" else text
    return template.format(**values) if values else template


def writing_rule():
    """The language rule for model prompts, which stay in Spanish."""
    if _notes == "en":
        return ("Escribe en inglés (English): título, contexto, encabezados, cuerpo, pies de imagen y razones, "
                "aunque la fuente o estas instrucciones estén en español.")
    return "Escribe en español."


def t(text, **values):
    return _text(_interface, text, values)


def n(text, **values):
    return _text(_notes, text, values)

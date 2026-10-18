import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "native"))
from core import App, UserError
from vault_profile import Profile, install

CLASSIC = json.loads((Path(__file__).resolve().parent / "fixtures/profile-classic.json").read_text())
GENERIC = {
    "schema": "anaco-profile/1",
    "types": {"nota": {"label": "Nota", "filename": "{title}.md"}},
    "destinations": [{"pattern": "Anaco", "types": ["nota"], "default": "nota", "derived": "nota"}],
    "frontmatter": [
        {"key": "tags", "from": "tags", "keep_empty": True},
        {"key": "fuente_url", "from": "url"},
        {"key": "fuente_autor", "from": "author"},
        {"key": "creado", "from": "created"},
        {"key": "relacionadas", "from": "relations", "keep_empty": True},
    ],
    "attachments": "Anaco/adjuntos",
    "relation_roots": [],
    "instructions": [],
    "sections": {},
}
CAPTURE = {"kind": "article", "created": "2026-10-18T10:00:00+02:00", "fingerprint": "abcdef123456", "url": "https://example.org/a", "author": "Ana"}


class ProfileTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.vault = self.root / "Vault"
        for folder in ("02_Cerebro/Tech_&_Codigo", "02_Cerebro/Modelos_Mentales", "03_Proyectos/App", "04_Cajon_Ideas", "07_Clases/01_Curso/01_Tema", "99_Recursos", "Anaco", ".obsidian", "02_Cerebro/.oculta"):
            (self.vault / folder).mkdir(parents=True, exist_ok=True)
        self.app = App(self.root / "state")
        self.app.set_config({"vault": str(self.vault), "provider": "manual"})

    def tearDown(self):
        self.app.db.close()
        self.temp.cleanup()

    def test_classic_profile_reproduces_previous_rules(self):
        install(self.app, CLASSIC, "99_Recursos/anaco/perfil.json")
        p = self.app.vault_profile()
        self.assertEqual(p.destinations(), ["02_Cerebro/Modelos_Mentales", "02_Cerebro/Tech_&_Codigo", "03_Proyectos", "03_Proyectos/App", "04_Cajon_Ideas", "07_Clases/01_Curso/01_Tema"])
        self.assertIn("modelo_mental", p.types_for("02_Cerebro/Modelos_Mentales"))
        self.assertNotIn("modelo_mental", p.types_for("02_Cerebro/Tech_&_Codigo"))
        self.assertEqual(p.default_type("07_Clases/01_Curso/01_Tema"), "resumen")
        self.assertEqual(p.default_type("07_Clases/01_Curso/01_Tema", derived=True), "apunte")
        self.assertTrue(p.study("07_Clases/01_Curso/01_Tema"))
        self.assertEqual(p.filename(CAPTURE, "Ideas Útiles!", "02_Cerebro/Tech_&_Codigo", "fuente_externa"), "fuente_2026-10-18_ideas_utiles.md")
        self.assertEqual(p.filename({**CAPTURE, "kind": "quote"}, "Cita", "02_Cerebro/Tech_&_Codigo", "fuente_externa"), "fuente_2026-10-18_cita_frase_abcdef.md")
        self.assertEqual(p.filename(CAPTURE, "Ideas Útiles", "02_Cerebro/Tech_&_Codigo", "indice"), "nota_indice_ideas_utiles.md")
        self.assertEqual(p.filename(CAPTURE, "Tema Uno", "07_Clases/01_Curso/01_Tema", "indice"), "indice_2026-10-18_tema-uno.md")
        p.validate_filename("resumen_2026-10-18_tema-uno.md", "resumen", "07_Clases/01_Curso/01_Tema")
        with self.assertRaises(UserError):
            p.validate_filename("nota_tema.md", "resumen", "07_Clases/01_Curso/01_Tema")
        with self.assertRaises(UserError):
            p.note_type("02_Cerebro/Tech_&_Codigo", "modelo_mental")
        fm = p.frontmatter({"type": "resumen", "folder": "07_Clases/01_Curso/01_Tema", "tags": ["iam"], "context": "c", "created": "2026-10-18", "today": "2026-10-19",
                            "assisted": False, "url": "https://example.org", "author": "A", "relations": []})
        self.assertEqual(list(fm), ["tipo", "tags", "estado", "contexto", "creado", "modificado", "version", "llm_asistido", "curso", "asignatura"])
        self.assertEqual(fm["tags"], ["clase", "iam", "ano-2026"])
        self.assertEqual((fm["curso"], fm["asignatura"]), ("Curso", "Tema"))

    def test_generic_profile_uses_title_and_minimal_metadata(self):
        install(self.app, GENERIC, "Anaco/perfil.json")
        p = self.app.vault_profile()
        self.assertEqual(p.destinations(), ["Anaco"])
        self.assertEqual(p.filename(CAPTURE, 'Guía: "CSS" / grid?', "Anaco", "nota"), "Guía CSS grid.md")
        p.validate_filename("Guía CSS grid.md", "nota", "Anaco")
        with self.assertRaises(UserError):
            p.validate_filename("../fuera.md", "nota", "Anaco")
        fm = p.frontmatter({"type": "nota", "folder": "Anaco", "tags": [], "created": "2026-10-18", "url": "https://example.org/a", "author": "",
                            "relations": [("02_Cerebro/Tech_&_Codigo/nota_x.md", "Nota X")]})
        self.assertEqual(fm, {"tags": [], "fuente_url": "https://example.org/a", "creado": "2026-10-18", "relacionadas": ["[[02_Cerebro/Tech_&_Codigo/nota_x|Nota X]]"]})

    def test_missing_profile_points_to_options_and_is_discovered_after_sync(self):
        with self.assertRaisesRegex(UserError, "Opciones"):
            self.app.vault_profile()
        # Another computer: the synced file is found without local configuration.
        target = self.vault / "99_Recursos/anaco/perfil.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(CLASSIC))
        self.assertEqual(self.app.vault_profile().path, "99_Recursos/anaco/perfil.json")

    def test_invalid_or_unsafe_profiles_are_rejected(self):
        bad = [
            {**GENERIC, "schema": "otro"},
            {**GENERIC, "attachments": "../fuera"},
            {**GENERIC, "attachments": ".obsidian/x"},
            {**GENERIC, "instructions": ["../../etc/passwd"]},
            {**GENERIC, "destinations": [{"pattern": "Anaco", "types": ["inexistente"], "default": "inexistente", "derived": "inexistente"}]},
            {**GENERIC, "types": {"nota": {"label": "Nota", "filename": "../{title}.md"}}},
            {**GENERIC, "frontmatter": [{"key": "x", "from": "desconocido"}]},
        ]
        for value in bad:
            with self.assertRaises(UserError, msg=json.dumps(value)[:120]):
                install(self.app, value, "Anaco/perfil.json")

    def test_hidden_folders_are_never_destinations(self):
        install(self.app, {**GENERIC, "destinations": [{"pattern": "**", "types": ["nota"], "default": "nota", "derived": "nota"}]}, "Anaco/perfil.json")
        self.assertFalse(any(part.startswith(".") for f in self.app.vault_profile().destinations() for part in f.split("/")))


if __name__ == "__main__":
    unittest.main()

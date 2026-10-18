import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "native"))
from core import App
from vault_profile import install
from vault_scan import scan, propose

SECRET = "SECRETO-PERSONAL-QUE-NO-SALE-DEL-ORDENADOR"


def note(path, fields, body="Contenido de la nota."):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for key, value in fields.items():
        lines.append(f"{key}: " + (json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value))
    path.write_text("---\n" + "\n".join(lines) + "\n---\n# " + path.stem + "\n\n" + body + "\n", encoding="utf-8")


def second_brain(root):
    """A reduced copy of the user's reorganized vault (shape, not content)."""
    v = root / "second_brain"
    (v / ".obsidian").mkdir(parents=True)
    (v / "AGENTS.md").write_text("---\ntipo: instrucciones_agente\nzona: sistema\n---\n# Trabajar en este Second Brain\n\nLeer la skill local [second-brain-vault](99_Recursos/skills/second-brain-vault/SKILL.md) y la [guía vigente](99_Recursos/guias/MANUAL_VAULT.md).\n")
    (v / "INBOX.md").write_text("---\ntipo: inbox\nzona: inbox\n---\n# Inbox\n")
    skill = v / "99_Recursos/skills/second-brain-vault/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: second-brain-vault\n---\n# Skill del vault\n\nCada nota lleva zona y relacionadas.\n")
    note(v / "99_Recursos/guias/MANUAL_VAULT.md", {"tipo": "guia", "zona": "recursos", "tags": [], "relacionadas": []}, "Manual vigente del vault.")
    note(v / "99_Recursos/guias/guia_frontmatter_y_relaciones.md", {"tipo": "guia", "zona": "recursos", "tags": [], "relacionadas": []}, "zona, area y relacionadas.")
    note(v / "99_Recursos/templates/template_fuente_externa.md", {"tipo": "fuente_externa", "zona": "diario", "tags": [], "relacionadas": []}, "## Resumen\n\n## Por qué lo guardo")
    note(v / "99_Recursos/templates/template_nota_atomica.md", {"tipo": "nota_atomica", "zona": "ideas", "tags": [], "relacionadas": []})
    (v / "99_Recursos/adjuntos").mkdir(parents=True)
    (v / "99_Recursos/adjuntos/imagen.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    note(v / "00_Sistema/identidad_viva.md", {"tipo": "nota_maestra", "zona": "sistema", "tags": [], "relacionadas": []}, SECRET)
    for i in range(6):
        note(v / f"02_Cerebro/Tech_&_Codigo/nota_tecnica_{i}.md", {"tipo": "nota_atomica", "zona": "cerebro", "area": "tech_codigo", "tags": ["css"], "relacionadas": ["[[02_Cerebro/Tech_&_Codigo/nota_tecnica_0]]"], "creado": "2026-10-0%d" % (i + 1), "metadatos_actualizados": "2026-10-18"}, SECRET)
    for i in range(3):
        note(v / f"02_Cerebro/Tech_&_Codigo/fuente_2026-10-1{i}_articulo_{i}.md", {"tipo": "fuente_externa", "zona": "cerebro", "area": "tech_codigo", "tags": [], "relacionadas": [], "creado": "2026-10-1%d" % i, "fuente_url": f"https://example.org/{i}", "fuente_autor": "Autor", "formato": "articulo"})
    for i in range(4):
        note(v / f"02_Cerebro/Modelos_Mentales/nota_modelo_{i}.md", {"tipo": "modelo_mental", "zona": "cerebro", "area": "modelos_mentales", "tags": [], "relacionadas": [], "creado": "2026-09-0%d" % (i + 1)})
    for i in range(3):
        note(v / f"03_Proyectos/homelab/nota_homelab_{i}.md", {"tipo": "nota_proyecto", "zona": "proyectos", "proyecto": "[[homelab]]", "tags": [], "relacionadas": []})
    for i in range(3):
        note(v / f"07_Clases/01_Habilitacion_Docencia/02_Programacion/ejercicio_2026-10-0{i + 1}_tarea-{i}.md", {"tipo": "ejercicio", "zona": "clases", "curso": "Habilitacion Docencia", "asignatura": "Programacion", "tags": [], "relacionadas": []})
    for i in range(5):
        note(v / f"05_Archivo_Legacy/Diario_etapa_2026/registro_{i}.md", {"tipo": "registro", "zona": "archivo", "estado": "legacy", "tags": [], "relacionadas": []})
    note(v / "01_Diario/indice_diario.md", {"tipo": "indice", "zona": "diario", "tags": [], "relacionadas": []})
    return v


class VaultScanTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def app_for(self, vault):
        app = App(self.root / ("state-" + vault.name))
        app.set_config({"vault": str(vault), "provider": "manual"})
        self.addCleanup(app.db.close)
        return app

    def test_facts_find_instructions_and_never_carry_note_bodies(self):
        facts = scan(self.app_for(second_brain(self.root)))
        paths = [d["path"] for d in facts["documents"]]
        for expected in ("AGENTS.md", "99_Recursos/skills/second-brain-vault/SKILL.md", "99_Recursos/guias/MANUAL_VAULT.md", "99_Recursos/guias/guia_frontmatter_y_relaciones.md", "99_Recursos/templates/template_fuente_externa.md"):
            self.assertIn(expected, paths)
        self.assertNotIn("00_Sistema/identidad_viva.md", paths)
        suggested = {d["path"] for d in facts["documents"] if d["suggested"]}
        self.assertIn("99_Recursos/guias/guia_frontmatter_y_relaciones.md", suggested)
        self.assertNotIn(SECRET, json.dumps(facts, ensure_ascii=False))
        self.assertEqual(facts["roles"]["templates"], "99_Recursos/templates")
        self.assertEqual(facts["roles"]["attachments"], "99_Recursos/adjuntos")
        self.assertIn("05_Archivo_Legacy", facts["roles"]["archive"])

    def test_deterministic_proposal_follows_the_reorganized_vault(self):
        app = self.app_for(second_brain(self.root))
        proposal = propose(scan(app))
        profile = install(app, proposal["profile"], "99_Recursos/anaco/perfil.json")
        destinations = profile.destinations()
        self.assertIn("02_Cerebro/Tech_&_Codigo", destinations)
        self.assertIn("07_Clases/01_Habilitacion_Docencia/02_Programacion", destinations)
        for excluded in ("05_Archivo_Legacy/Diario_etapa_2026", "99_Recursos/templates", "99_Recursos/guias", "01_Diario", "00_Sistema"):
            self.assertNotIn(excluded, destinations)
        self.assertEqual(profile.default_type("02_Cerebro/Tech_&_Codigo"), "nota_atomica")
        self.assertIn("fuente_externa", profile.types_for("02_Cerebro/Tech_&_Codigo"))
        self.assertEqual(profile.filename({"kind": "article", "created": "2026-10-18T09:00:00", "fingerprint": "f" * 12}, "Grid y subgrid", "02_Cerebro/Tech_&_Codigo", "fuente_externa"), "fuente_2026-10-18_grid_y_subgrid.md")
        self.assertEqual(profile.filename({"kind": "article", "created": "2026-10-18T09:00:00", "fingerprint": "f" * 12}, "Tarea nueva", "07_Clases/01_Habilitacion_Docencia/02_Programacion", "ejercicio"), "ejercicio_2026-10-18_tarea-nueva.md")
        fm = profile.frontmatter({"type": "fuente_externa", "folder": "02_Cerebro/Tech_&_Codigo", "tags": ["css"], "created": "2026-10-18", "today": "2026-10-18",
                                  "url": "https://example.org/x", "author": "Ana", "source_format": "articulo", "relations": [("02_Cerebro/Modelos_Mentales/nota_modelo_0.md", "Modelo 0")]})
        self.assertEqual(fm["tipo"], "fuente_externa")
        self.assertEqual(fm["zona"], "cerebro")
        self.assertEqual(fm["area"], "tech_codigo")
        self.assertEqual(fm["relacionadas"], ["[[02_Cerebro/Modelos_Mentales/nota_modelo_0|Modelo 0]]"])
        self.assertEqual(fm["fuente_url"], "https://example.org/x")
        self.assertNotIn("version", fm)
        # Course fields come from the path only where courses live.
        self.assertNotIn("curso", fm)
        clase = profile.frontmatter({"type": "ejercicio", "folder": "07_Clases/01_Habilitacion_Docencia/02_Programacion", "tags": [], "created": "2026-10-18", "relations": []})
        self.assertEqual((clase["zona"], clase["curso"], clase["asignatura"], clase["relacionadas"]), ("clases", "Habilitacion Docencia", "Programacion", []))
        self.assertIn("99_Recursos/guias/MANUAL_VAULT.md", profile.data["instructions"])
        self.assertTrue(proposal["evidence"])

    def test_vault_without_conventions_gets_the_generic_profile(self):
        v = self.root / "plain"
        (v / ".obsidian").mkdir(parents=True)
        (v / "Lecturas").mkdir()
        (v / "Lecturas" / "Un libro.md").write_text("Sin metadatos.\n")
        (v / "Lecturas" / "Otro libro.md").write_text("Tampoco.\n")
        app = self.app_for(v)
        profile = install(app, propose(scan(app))["profile"], "anaco/perfil.json")
        self.assertEqual(profile.destinations(), ["Lecturas"])
        self.assertEqual(profile.filename({"kind": "article", "created": "2026-10-18", "fingerprint": "a" * 12}, "Mi nota: CSS", "Lecturas", None), "Mi nota CSS.md")
        fm = profile.frontmatter({"type": profile.default_type("Lecturas"), "folder": "Lecturas", "tags": [], "created": "2026-10-18", "url": "https://example.org", "author": "Ana", "relations": []})
        self.assertEqual(list(fm), ["tags", "fuente_url", "fuente_autor", "creado"])

    def test_empty_vault_proposes_an_anaco_folder_created_on_confirmation(self):
        v = self.root / "vacio"
        (v / ".obsidian").mkdir(parents=True)
        app = self.app_for(v)
        profile = install(app, propose(scan(app))["profile"], "Anaco/perfil.json")
        self.assertTrue((v / "Anaco").is_dir())
        self.assertEqual(profile.destinations(), ["Anaco"])


if __name__ == "__main__":
    unittest.main()


class VaultInterpretationTest(unittest.TestCase):
    setUp = VaultScanTest.setUp
    tearDown = VaultScanTest.tearDown
    app_for = VaultScanTest.app_for

    def answer(self, base):
        """A model answer in list form, refining the deterministic proposal."""
        p = base["profile"]
        return {
            "types": [{"key": k, "label": v["label"], "filename": v["filename"]} for k, v in p["types"].items()],
            "destinations": [{"pattern": r["pattern"], "types": r["types"], "default": r["default"], "derived": r["derived"], "study": r["pattern"].startswith("07_Clases")} for r in p["destinations"]],
            "frontmatter": [{"key": f["key"], "from": f["from"], "value": str(f.get("value", "")), "index": f.get("index", -1), "keep_empty": bool(f.get("keep_empty")),
                             "values": [{"folder": k, "value": v} for k, v in f.get("values", {}).items()], "when_types": f.get("when", {}).get("types", []),
                             "when_folders": [], "when_assisted": "any" if "assisted" not in f.get("when", {}) else "yes"} for f in p["frontmatter"]],
            "attachments": p["attachments"], "relation_roots": p["relation_roots"], "instructions": p["instructions"],
            "default_destination": p["default_destination"],
            "sections": [{"key": "relations", "heading": "Relacionadas"}],
            "explanations": [{"rule": "frontmatter:zona", "explanation": "La guía de frontmatter define zona por carpeta."}],
        }

    def test_model_reads_only_chosen_documents_and_never_note_bodies(self):
        from vault_scan import interpret
        app = self.app_for(second_brain(self.root))
        app.set_config({"provider": "codex"})
        sent = {}
        def fake(prompt, spec, model=None, images=None):
            sent["prompt"] = prompt
            return self.answer(propose(scan(app)))
        from unittest.mock import patch
        with patch.object(app, "codex_json", side_effect=fake):
            result = interpret(app, ["AGENTS.md", "99_Recursos/guias/guia_frontmatter_y_relaciones.md", "00_Sistema/identidad_viva.md"])
        self.assertIn("Leer la skill local", sent["prompt"])
        self.assertIn("zona, area y relacionadas", sent["prompt"])
        # Not an instruction document: rejected even if requested.
        self.assertNotIn(SECRET, sent["prompt"])
        self.assertNotIn("Manual vigente del vault", sent["prompt"])
        self.assertEqual(result["profile"]["sections"], {"relations": "Relacionadas"})
        self.assertIn("frontmatter:zona", result["evidence"])
        self.assertTrue(result["assisted"])

    def test_invented_folders_or_documents_fall_back_to_the_scan(self):
        from vault_scan import interpret
        app = self.app_for(second_brain(self.root))
        app.set_config({"provider": "codex"})
        bad = self.answer(propose(scan(app)))
        bad["destinations"].append({"pattern": "Inventada/Carpeta", "types": ["nota_atomica"], "default": "nota_atomica", "derived": "nota_atomica", "study": False})
        bad["instructions"].append("00_Sistema/identidad_viva.md")
        from unittest.mock import patch
        with patch.object(app, "codex_json", return_value=bad):
            result = interpret(app, ["AGENTS.md"])
        patterns = [r["pattern"] for r in result["profile"]["destinations"]]
        self.assertNotIn("Inventada/Carpeta", patterns)
        self.assertNotIn("00_Sistema/identidad_viva.md", result["profile"]["instructions"])
        self.assertTrue(result["warnings"])

    def test_manual_mode_uses_the_deterministic_proposal(self):
        from vault_scan import interpret
        app = self.app_for(second_brain(self.root))
        from unittest.mock import patch
        with patch.object(app, "codex_json", side_effect=AssertionError("no AI in manual mode")):
            result = interpret(app, ["AGENTS.md"])
        self.assertFalse(result["assisted"])
        self.assertEqual(result["profile"], propose(scan(app))["profile"])


class ProfileActionsTest(unittest.TestCase):
    setUp = VaultScanTest.setUp
    tearDown = VaultScanTest.tearDown
    app_for = VaultScanTest.app_for

    def test_scan_review_and_save_round_trip(self):
        app = self.app_for(second_brain(self.root))
        self.assertTrue(app.handle({"action": "profile_get"})["missing"])
        scanned = app.handle({"action": "profile_scan"})
        self.assertEqual(scanned["suggested_path"], "99_Recursos/anaco/perfil.json")
        self.assertNotIn(SECRET, json.dumps(scanned, ensure_ascii=False))
        saved = app.handle({"action": "profile_save", "profile": scanned["proposal"]["profile"], "path": scanned["suggested_path"]})
        self.assertEqual(saved["path"], "99_Recursos/anaco/perfil.json")
        self.assertEqual(app.handle({"action": "profile_get"})["path"], saved["path"])
        self.assertIn("02_Cerebro/Tech_&_Codigo", app.handle({"action": "status"})["folders"])

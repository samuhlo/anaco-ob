import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "native"))
from core import UserError
import test_core as core_tests


class ServiceLanguageTest(unittest.TestCase):
    setUp = core_tests.CoreTest.setUp
    tearDown = core_tests.CoreTest.tearDown

    def test_errors_follow_the_interface_language(self):
        with self.assertRaisesRegex(UserError, "Acción desconocida"):
            self.app.handle({"action": "nope"})
        with self.assertRaisesRegex(UserError, "Unknown action"):
            self.app.handle({"action": "nope", "lang": "en"})
        # An unknown language keeps Spanish, the main language.
        with self.assertRaisesRegex(UserError, "Identificador de captura no válido"):
            self.app.handle({"action": "preview", "id": "x", "lang": "fr"})

    def test_messages_with_values_are_translated_whole(self):
        from translation import t, set_language
        set_language("en")
        self.addCleanup(set_language, "es")
        self.assertEqual(t("El destino {pattern} no tiene ninguna carpeta en el vault.", pattern="03_Proyectos/**"),
                         "The destination 03_Proyectos/** has no folder in the vault.")

    def test_every_service_text_has_an_english_translation(self):
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root / "scripts"))
        import i18n as tool
        self.assertEqual(tool.native_problems(), [])


class NoteLanguageTest(unittest.TestCase):
    setUp = core_tests.CoreTest.setUp
    tearDown = core_tests.CoreTest.tearDown
    capture = core_tests.CoreTest.capture

    def preview(self):
        c = self.capture()
        self.app.handle({"action": "draft", "id": c["id"], "provider": "manual"})
        return self.app.handle({"action": "preview", "id": c["id"], "fields": {}})["markdown"]

    def test_notes_stay_in_spanish_by_default(self):
        markdown = self.preview()
        self.assertIn("## Fuente", markdown)
        self.assertIn("[Abrir original]", markdown)
        self.assertEqual(self.app.handle({"action": "settings"})["default_sections"]["source"], "Fuente")

    def test_english_notes_use_english_headings_and_fixed_texts(self):
        self.app.set_config({"note_language": "en"})
        markdown = self.preview()
        self.assertIn("## Source", markdown)
        self.assertIn("[Open original]", markdown)
        self.assertNotIn("## Fuente", markdown)
        # The interface language does not change the notes.
        self.assertEqual(self.app.handle({"action": "settings", "lang": "es"})["default_sections"]["summary"], "Summary")
        with self.assertRaises(UserError):
            self.app.set_config({"note_language": "fr"})

    def test_prompts_ask_for_the_note_language(self):
        answer = {"title": "Active recall", "context": "Study", "body": "A summary.", "folder": "02_Cerebro/Modelos_Mentales",
                  "tags": ["learning"], "relations": []}
        prompts = []
        def generate(prompt, *args, **kwargs):
            prompts.append(prompt)
            return answer
        for language in ("es", "en"):
            self.app.set_config({"note_language": language})
            c = self.capture(url=f"https://example.org/{language}")
            with patch.object(self.app, "ai_json", side_effect=generate):
                self.app.handle({"action": "draft", "id": c["id"], "provider": "codex"})
        self.assertIn("Escribe en español.", prompts[0])
        self.assertIn("English", prompts[1])
        self.assertNotIn("Escribe en español.", prompts[1])


if __name__ == "__main__":
    unittest.main()

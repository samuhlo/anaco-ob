import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'native'))
from core import UserError
from editorial_profile import compact_guide
import test_core as core_tests


class EditorialProfileTest(unittest.TestCase):
    setUp = core_tests.CoreTest.setUp
    tearDown = core_tests.CoreTest.tearDown

    def guide(self, suffix=''):
        document = ('Reglas de ejemplo para un vault de pruebas.\n' * 350
                    + 'Preferir fuente_externa para podcasts. No imponer plantillas. '
                    + 'Conservar excepciones y distinguir sugerencias del editor.' + suffix)
        return {'instructions': 'Contrato íntegro de la aplicación.',
                'documents': {'guia.md': document}, 'hash': hashlib.sha256(document.encode()).hexdigest()}

    def compiled(self):
        return {'instructions': ('Preferir fuente_externa para podcasts. No imponer plantillas. '
                                 'Conservar excepciones y distinguir sugerencias del editor. '
                                 'Las reglas del vault tienen prioridad.'), 'complete': True}

    def test_full_documents_are_compiled_once_with_luna_and_contract_stays_intact(self):
        guide = self.guide()
        self.app.set_config({'provider': 'codex'})
        with patch.object(self.app, 'codex_json', return_value=self.compiled()) as ai:
            result = compact_guide(self.app, guide)
            again = compact_guide(self.app, guide)
        self.assertEqual(ai.call_count, 1)
        prompt, _, model, _ = ai.call_args.args
        self.assertEqual(model, 'gpt-6-luna')
        self.assertIn(guide['documents']['guia.md'].splitlines()[-1], prompt)
        self.assertEqual(result, again)
        self.assertEqual(result['instructions'], guide['instructions'])
        self.assertEqual(result['hash'], guide['hash'])
        self.assertEqual(result['documents']['editorial'], self.compiled()['instructions'])
        self.assertLess(len(json.dumps(result)), len(json.dumps(guide)))

    def test_guides_and_reader_settings_invalidate_but_final_model_does_not(self):
        with patch.object(self.app, 'codex_json', return_value=self.compiled()) as ai:
            compact_guide(self.app, self.guide())
            self.app.set_config({'model': 'new-writer'})
            compact_guide(self.app, self.guide())
            self.assertEqual(ai.call_count, 1)
            compact_guide(self.app, self.guide('Una excepción nueva.'))
            self.app.set_config({'reading_model': 'new-reader'})
            compact_guide(self.app, self.guide())
            self.app.set_config({'reasoning_effort': 'high'})
            compact_guide(self.app, self.guide())
            self.assertEqual(ai.call_count, 4)

    def test_uncertain_invalid_or_failed_compilation_keeps_all_original_rules(self):
        guide = self.guide()
        for value in ({**self.compiled(), 'complete': False}, {}, {'instructions': 'too short', 'complete': True}):
            with self.subTest(value=value), patch.object(self.app, 'codex_json', return_value=value):
                self.assertEqual(compact_guide(self.app, guide), guide)
        with patch.object(self.app, 'codex_json', side_effect=UserError('Sin respuesta')):
            self.assertEqual(compact_guide(self.app, guide), guide)
        self.assertEqual(list((self.app.state / 'editorial-profiles').glob('*.json')), [])

    def test_short_guides_do_not_need_an_extra_request(self):
        guide = {'instructions': 'Contrato.', 'documents': {'guia.md': 'Reglas propias.'}, 'hash': 'short'}
        with patch.object(self.app, 'ai_json') as ai:
            self.assertEqual(compact_guide(self.app, guide), guide)
        ai.assert_not_called()

    def test_cancellation_propagates_instead_of_starting_generation(self):
        from jobs import Cancelled
        with patch.object(self.app, 'codex_json', side_effect=Cancelled()), patch.object(self.app, 'check_cancel', side_effect=[None, Cancelled()]):
            with self.assertRaises(Cancelled):
                compact_guide(self.app, self.guide())

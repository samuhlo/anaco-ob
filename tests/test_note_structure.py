import copy
from unittest.mock import patch
import test_core as base
import test_editorial as editorial_base
from core import UserError


class NoteStructureTest(base.unittest.TestCase):
    setUp=base.CoreTest.setUp
    tearDown=base.CoreTest.tearDown

    def proposal(self):
        capture, result=editorial_base.EditorialTest.collection(self)
        self.app.set_config({'note_structure':'single'})
        result['notes'][0]['body']+='\n\n```js\nconst amount = 0.5;\n```'
        return capture,result

    def test_single_is_default_and_keeps_all_sections_code_and_page_references(self):
        self.assertEqual(self.app.config()['note_structure'],'single')
        c,result=self.proposal()
        with patch.object(self.app,'codex_generate',return_value=result):self.app.draft(c['id'],provider='codex')
        stored=self.app.load(c['id'])
        self.assertNotIn('bundle',stored)
        self.assertEqual(stored['draft']['source_pages'],[1,2])
        for note in result['notes']:self.assertIn(note['body'],stored['draft']['body'])
        self.assertIn('```js\nconst amount = 0.5;\n```',self.app.preview(c['id'],{})['markdown'])

    def test_capture_choice_overrides_default_and_retry_keeps_it(self):
        c,result=self.proposal()
        with patch.object(self.app,'codex_generate',side_effect=UserError('interrumpido')):
            with self.assertRaises(UserError):self.app.draft(c['id'],provider='codex',note_structure='linked')
        self.assertEqual(self.app.load(c['id'])['note_structure'],'linked')
        with patch.object(self.app,'codex_generate',return_value=result):self.app.draft(c['id'],provider='codex')
        self.assertEqual(len(self.app.load(c['id'])['bundle']['notes']),2)

    def test_automatic_can_accept_either_one_note_or_a_collection(self):
        c,result=self.proposal()
        for proposal in (result,{**result,'notes':[]}):
            with patch.object(self.app,'codex_generate',return_value=copy.deepcopy(proposal)):
                self.app.draft(c['id'],provider='codex',note_structure='auto')
            self.assertEqual(bool(self.app.load(c['id']).get('bundle')),bool(proposal['notes']))

    def test_invalid_structure_never_changes_configuration_or_capture(self):
        c,_=self.proposal()
        config=self.app.config()
        with self.assertRaises(UserError):self.app.set_config({'note_structure':'invalid'})
        self.assertEqual(self.app.config(),config)
        before=self.app.load(c['id'])
        with self.assertRaises(UserError):self.app.draft(c['id'],provider='manual',note_structure='invalid')
        self.assertEqual(self.app.load(c['id']),before)

    def test_single_mode_still_rejects_invented_page_references(self):
        c,result=self.proposal();result['notes'][0]['pages']=[99]
        with patch.object(self.app,'codex_generate',return_value=result):
            with self.assertRaises(UserError):self.app.draft(c['id'],provider='codex',note_structure='single')

import copy
import json
from unittest.mock import patch
import test_core as base
from core import UserError
from splitting import blocks

BODY='## Caché\nGuardar el glifo evita rasterizarlo en cada cuadro.\n\n````js\nconst label = `\n## Esto es código, no un apartado\n`;\nconst fence = "```";\n````\n\n## Ondulación\nLas franjas horizontales se desplazan para deformar la letra.\n\n## Comentario personal\nMI ANOTACIÓN EXACTA: probar primero con una letra.\n'


class SplittingTest(base.unittest.TestCase):
    setUp=base.CoreTest.setUp
    tearDown=base.CoreTest.tearDown

    def prepared(self):
        c=self.app.stage({'kind':'article','url':'https://example.org/tutorial','title':'Glifos animados','text':BODY})
        self.app.draft(c['id'],provider='manual')
        fields={'notes':{'source':{'body':BODY,'title':'Título editado por mí','captions':{},'images':[]}},'selected_notes':['source'],'active_note':'source','merged_into':{}}
        return c,fields

    def answer(self):
        return {'recommended':True,'rationale':'La caché y la deformación se pueden consultar por separado.','summary':'Caché y ondulación cooperan para dibujar los glifos.',
                'groups':[{'title':'Caché de glifos','purpose':'Reutilizar el dibujo sin repetir la rasterización.','note_type':'nota_atomica','block_ids':[0,2],'images':[]},
                          {'title':'Deformación por franjas','purpose':'Comprender cómo se deforma cada letra.','note_type':'referencia_tecnica','block_ids':[1],'images':[]}]}

    def propose(self,c,fields,answer=None):
        with patch.object(self.app,'codex_json',return_value=answer or self.answer()):
            return self.app.handle({'action':'propose_split','id':c['id'],'note':'source','fields':fields})

    def test_blocks_keep_every_character_and_never_split_inside_code(self):
        parts=blocks(BODY)
        self.assertEqual(len(parts),3)
        self.assertEqual(''.join(p['body'] for p in parts),BODY)
        self.assertIn('## Esto es código, no un apartado',parts[0]['body'])

    def test_proposal_and_discard_leave_original_capture_and_vault_intact(self):
        c,fields=self.prepared();before=self.app.load(c['id'])
        proposal=self.propose(c,fields)
        self.assertTrue(proposal['recommended']);self.assertEqual(len(proposal['notes']),2)
        self.assertEqual(self.app.load(c['id']),before)
        for part in blocks(BODY):self.assertEqual(sum(part['body'] in n['body'] for n in proposal['notes']),1)
        self.app.handle({'action':'split_decision','id':c['id'],'proposal':proposal['id'],'decision':'discard'})
        self.assertEqual(self.app.load(c['id']),before)
        self.assertFalse(list(self.vault.rglob('*.md')))

    def test_accept_keeps_edits_code_annotations_and_creates_reviewable_links(self):
        c,fields=self.prepared();proposal=self.propose(c,fields)
        applied=self.app.handle({'action':'split_decision','id':c['id'],'proposal':proposal['id'],'decision':'accept','fields':fields})
        self.assertEqual(applied['count'],3)
        stored=self.app.load(c['id']);self.assertEqual(stored['draft']['title'],'Título editado por mí')
        children=stored['bundle']['notes'];self.assertEqual(len(children),2)
        self.assertIn('MI ANOTACIÓN EXACTA',children[0]['body']);self.assertIn('const fence = "```";',children[0]['body'])
        root=self.app.preview(c['id'],applied['fields'])
        self.assertEqual(len(root['internal_links']),2)
        for n in children:
            preview=self.app.preview(c['id'],{**applied['fields'],'active_note':n['id']})
            self.assertTrue(any(link['id']=='source' for link in preview['internal_links']))
        self.assertFalse(list(self.vault.rglob('*.md')))
        saved=self.app.save(c['id'],applied['fields']);self.assertEqual(saved['count'],3)

    def test_unknown_missing_or_repeated_blocks_are_rejected_without_mutating_note(self):
        c,fields=self.prepared();before=self.app.load(c['id'])
        for ids in ([0],[0,2,1],[0,2,99]):
            answer=self.answer();answer['groups'][0]['block_ids']=ids
            with self.assertRaises(UserError):self.propose(c,fields,answer)
        self.assertEqual(self.app.load(c['id']),before)

    def test_accept_requires_explicit_decision_and_rejects_new_edits(self):
        c,fields=self.prepared();proposal=self.propose(c,fields)
        message={'action':'split_decision','id':c['id'],'proposal':proposal['id'],'fields':fields}
        with self.assertRaises(UserError):self.app.handle(message)
        newer=copy.deepcopy(fields);newer['notes']['source']['body']+='NUEVA EDICIÓN'
        with self.assertRaises(UserError):self.app.handle({**message,'decision':'accept','fields':newer})
        self.assertNotIn('bundle',self.app.load(c['id']))

    def test_accept_rejects_a_changed_or_already_saved_native_draft(self):
        c,fields=self.prepared();proposal=self.propose(c,fields)
        stored=self.app.load(c['id']);stored['draft']['body']+='Cambio externo';self.app.store(stored)
        with self.assertRaises(UserError):self.app.handle({'action':'split_decision','id':c['id'],'proposal':proposal['id'],'decision':'accept','fields':fields})
        self.assertNotIn('bundle',self.app.load(c['id']))

    def test_model_can_recommend_keeping_one_note(self):
        c,fields=self.prepared();before=self.app.load(c['id'])
        result=self.propose(c,fields,{'recommended':False,'rationale':'Un solo mecanismo; separar duplicaría las explicaciones.','summary':'','groups':[]})
        self.assertFalse(result['recommended']);self.assertNotIn('id',result)
        self.assertEqual(self.app.load(c['id']),before)

    def test_other_capture_cannot_accept_this_suggestion(self):
        c,fields=self.prepared();proposal=self.propose(c,fields);other,_=self.prepared()
        with self.assertRaises(UserError):self.app.handle({'action':'split_decision','id':other['id'],'proposal':proposal['id'],'decision':'accept','fields':fields})

    def test_images_and_edited_captions_follow_their_suggested_note(self):
        c=self.app.stage({'kind':'article','url':'https://example.org/figures','title':'Glifos','text':BODY,'images':[{'data':base.base64.b64encode(base.PNG).decode(),'alt':'Diagrama de caché de glifos y deformación por franjas.'}]})
        self.app.draft(c['id'],provider='manual')
        fields={'notes':{'source':{'body':BODY,'images':[0],'captions':{'0':'MI PIE EDITADO'}}},'selected_notes':['source'],'active_note':'source'}
        answer=self.answer();answer['groups'][1]['images']=[0]
        proposal=self.propose(c,fields,answer)
        applied=self.app.handle({'action':'split_decision','id':c['id'],'proposal':proposal['id'],'decision':'accept','fields':fields})
        stored=self.app.load(c['id']);child=stored['bundle']['notes'][1]
        self.assertEqual(applied['fields']['notes']['source']['images'],[])
        self.assertEqual(applied['fields']['notes'][child['id']]['images'],[0])
        rendered=self.app.preview(c['id'],{**applied['fields'],'active_note':child['id']})['markdown']
        self.assertIn('MI PIE EDITADO',rendered);self.assertIn('![[',rendered)

    def test_dividing_a_child_keeps_other_notes_and_their_edits(self):
        c,fields=self.prepared();proposal=self.propose(c,fields)
        first=self.app.handle({'action':'split_decision','id':c['id'],'proposal':proposal['id'],'decision':'accept','fields':fields})
        stored=self.app.load(c['id']);child,other=stored['bundle']['notes']
        edited=first['fields'];edited['active_note']=child['id'];edited['notes'][other['id']]['body']+='\nAPORTE A LA OTRA NOTA.'
        answer=self.answer();answer['groups'][0]['block_ids']=[0];answer['groups'][1]['block_ids']=[1]
        with patch.object(self.app,'codex_json',return_value=answer):
            suggested=self.app.handle({'action':'propose_split','id':c['id'],'note':child['id'],'fields':edited})
        second=self.app.handle({'action':'split_decision','id':c['id'],'proposal':suggested['id'],'decision':'accept','fields':edited})
        self.assertEqual(second['count'],5)
        self.assertIn('APORTE A LA OTRA NOTA.',second['fields']['notes'][other['id']]['body'])
        self.assertEqual(self.app.load(c['id'])['draft']['body'],stored['draft']['body'])

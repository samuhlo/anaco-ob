import copy
import json
from unittest.mock import patch
import test_core as base
from core import UserError

A='GSAP actualiza el progreso de animación que Canvas utiliza para dibujar los glifos. El renderizador lee valores sin animar cada elemento del DOM.'
B='El ticker de GSAP coordina el ciclo de renderizado y los tweens actualizan los valores de estado. Al desmontar el componente se elimina el callback.'
TARGET='El ticker de GSAP permite registrar un callback de renderizado. Al desmontar un componente se debe retirar con gsap.ticker.remove para evitar trabajo duplicado.'


class LinkingTest(base.unittest.TestCase):
    setUp=base.CoreTest.setUp
    tearDown=base.CoreTest.tearDown

    def prepared(self):
        path='02_Cerebro/Tech_&_Codigo/nota_gsap_ticker.md';(self.vault/path).write_text('# GSAP y su ticker\n\n'+TARGET)
        c=self.app.stage({'kind':'article','title':'Canvas and animation state','url':'https://example.org/tutorial','text':'The rendering clock updates state consumed by a Canvas renderer. This English source differs from the Spanish study notes.'})
        self.app.draft(c['id'],provider='manual');c=self.app.load(c['id']);c['draft']['body']='Canvas y GSAP separan dibujo y animación para coordinar el efecto.'
        children=[]
        for key,title,body in [('tema-canvas','Dibujar los glifos con Canvas',A),('tema-reloj','Coordinar el ciclo con GSAP',B)]:
            children.append({**copy.deepcopy(c['draft']),'id':key,'title':title,'body':body,'filename':'nota_'+key.replace('-','_')+'.md','note_type':'nota_atomica','links':[]})
        c['bundle']={'rationale':'Dibujo y coordinación','notes':children};self.app.store(c)
        fields={'notes':{},'selected_notes':['source','tema-canvas','tema-reloj'],'active_note':'tema-canvas'}
        return c,fields,path

    def plan(self,prompt,spec):
        data=json.loads(prompt.split('\n\n',1)[1]);target=next(n for n in data['candidates'] if 'GSAP' in n['title'])
        a=next(n for n in data['notes'] if n['id']=='tema-canvas');b=next(n for n in data['notes'] if n['id']=='tema-reloj')
        return {'existing':[{'from':a['id'],'to':target['id'],'from_evidence':a['evidence'][0]['id'],'to_evidence':target['evidence'][0]['id'],'kind':'aplica','reason':'La coordinación de GSAP explica cómo actualizar y limpiar el callback que dibuja el canvas.'}],
                'internal':[{'from':a['id'],'to':b['id'],'from_evidence':a['evidence'][0]['id'],'to_evidence':b['evidence'][0]['id'],'kind':'requisito','reason':'El renderizador Canvas consume el estado actualizado por el ticker y los tweens de GSAP.'}]}

    def refresh(self,c,fields):
        with patch.object(self.app,'codex_json',side_effect=self.plan):return self.app.handle({'action':'refresh_links','id':c['id'],'fields':fields})

    def test_links_use_literal_edited_note_evidence_even_when_source_language_differs(self):
        c,fields,path=self.prepared();result=self.refresh(c,fields);relation=result['notes']['tema-canvas']['relations'][0]
        self.assertEqual(relation['path'],path);self.assertEqual(relation['evidence_origin'],'note')
        self.assertIn(relation['source_evidence'],A);self.assertNotIn(relation['source_evidence'],c['text'])
        self.assertIn(relation['note_evidence'],TARGET);self.assertFalse(relation['accepted'])
        fields['notes']['tema-canvas']={'relations':[path]}
        rendered=self.app.preview(c['id'],fields)['markdown']
        self.assertIn('[[02_Cerebro/Tech_&_Codigo/nota_gsap_ticker]]',rendered)
        self.assertIn('llm_asistido: true',rendered);self.assertIn('llm_modelo: "gpt-6-luna"',rendered)
        unused=copy.deepcopy(fields);unused['notes']['tema-canvas']={'relations':[],'excluded_links':['tema-reloj']}
        self.assertIn('llm_asistido: false',self.app.preview(c['id'],unused)['markdown'])
        self.assertEqual(self.app.load(c['id'])['bundle']['notes'][0]['body'],A)

    def test_thematic_links_are_reciprocal_and_respect_exclusion(self):
        c,fields,_=self.prepared();result=self.refresh(c,fields)
        self.assertEqual(result['stats']['internal'],1)
        for key,target in [('tema-canvas','tema-reloj'),('tema-reloj','tema-canvas')]:
            preview=self.app.preview(c['id'],{**fields,'active_note':key})
            self.assertTrue(any(r['id']==target and r['accepted'] for r in preview['internal_links']))
        fields['notes']['tema-canvas']={'excluded_links':['tema-reloj']}
        preview=self.app.preview(c['id'],{**fields,'active_note':'tema-reloj'})
        self.assertTrue(any(r['id']=='tema-canvas' and not r['accepted'] for r in preview['internal_links']))

    def test_invalid_ids_and_evidence_never_make_a_relationship(self):
        c,fields,_=self.prepared()
        def bad(prompt,spec):
            result=self.plan(prompt,spec);result['existing'][0]['to']='../../outside';result['internal'][0]['from_evidence']=999;return result
        with patch.object(self.app,'codex_json',side_effect=bad):result=self.app.handle({'action':'refresh_links','id':c['id'],'fields':fields})
        self.assertEqual(result['stats']['external'],0);self.assertEqual(result['stats']['internal'],0);self.assertEqual(result['stats']['rejected'],2)

    def test_new_edit_invalidates_evidence_and_refresh_can_recover(self):
        c,fields,path=self.prepared();self.refresh(c,fields)
        fields['notes']['tema-canvas']={'body':'Un contenido nuevo que ya no habla de animación ni de renderizado.','relations':[path]}
        with self.assertRaises(UserError):self.app.preview(c['id'],fields)
        with patch.object(self.app,'codex_json',return_value={'existing':[],'internal':[]}):result=self.app.handle({'action':'refresh_links','id':c['id'],'fields':fields})
        self.assertEqual(result['notes']['tema-canvas']['relations'],[])
        self.assertFalse(any(r['id']=='tema-reloj' for r in result['notes']['tema-canvas']['links']))
        self.assertFalse(any(r['id']=='tema-canvas' for r in result['notes']['tema-reloj']['links']))

    def test_internal_link_disappears_when_its_target_is_not_selected(self):
        c,fields,_=self.prepared();self.refresh(c,fields)
        fields['selected_notes']=['source','tema-canvas']
        preview=self.app.preview(c['id'],fields)
        self.assertFalse(any(r['id']=='tema-reloj' for r in preview['internal_links']))

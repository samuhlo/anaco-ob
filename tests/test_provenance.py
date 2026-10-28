import json
from pathlib import Path
import unittest
from unittest.mock import patch
import test_core
from core import UserError
from provenance import resolve


class ProvenanceTest(unittest.TestCase):
    def setUp(self):
        test_core.CoreTest.setUp(self)
        from vault_profile import install
        profile = json.loads(test_core.CLASSIC.read_text())
        for rule in profile['destinations']:
            if rule['pattern'].startswith('07_Clases'):
                rule['pattern'] = '07_Clases/**'
        install(self.app, profile, '99_Recursos/anaco/perfil.json')
    tearDown = test_core.CoreTest.tearDown

    def group(self, suffix, facts):
        folder = '07_Clases/01_Curso/01_Tema/' + suffix
        path = self.vault / folder
        path.mkdir(parents=True)
        (path / 'existing.md').write_text('---\n' + '\n'.join(k + ': ' + json.dumps(v) for k, v in facts.items()) + '\n---\nOriginal conservado')
        (path / 'index.md').write_text('---\ntipo: indice\n---\n# Índice\n\nTabla original\n')
        return folder

    def prepare(self, title, catalog, topic, url='https://example.org/resource'):
        c = self.app.stage({'kind':'video', 'url':url, 'title':title, 'text':'Transcripción original completa sobre ' + topic,
                            'source_context':{'catalog':catalog,'resource_title':title,'page_url':'https://course.example/catalog'}})
        result = {'title':topic,'context':'Contenido de la captura','body':'Transcripción original completa sobre ' + topic,
                  'folder':self.app.folders()[0],'tags':[],'relations':[]}
        with patch.object(self.app, 'codex_generate', return_value=result):
            draft = self.app.draft(c['id'], provider='codex')
        return c, draft

    def test_four_representative_imports_and_reimport(self):
        professor = self.group('teoria/01_Profesora/UD01', {'origen':'Profesora de MP5160','unidad_didactica':'UD01','modulo':'MP5160'})
        aws = self.group('teoria/02_AWS/02_Economia', {'origen':'AWS Academy','curso_fuente':'AWS Academy Cloud Foundations','modulo_aws':2,'modulo':'MP5160'})
        cases = [
            ('Apartado 05', 'MP5160 > Profesora > UD01', 'Infraestructura física y recursos lógicos', professor, 'Apartado 05'),
            ('Module 2 - Section 3', 'AWS Academy Cloud Foundations', 'AWS Organizations', aws, 'M02 · S03'),
            ('Module 2 - Case study Delaware North', 'AWS Academy Cloud Foundations', 'Caso Delaware North · Evaluación de la migración', aws, 'M02'),
            ('Servicios cloud', '', 'Comparación de recursos físicos y virtuales', None, None),
        ]
        for i, (original,catalog,topic,folder,expected) in enumerate(cases):
            with self.subTest(original=original):
                url = 'https://drive.google.com/file/d/test/view' if i == 0 else 'https://example.org/resource/' + str(i)
                c, result = self.prepare(original,catalog,topic,url)
                preview = self.app.preview(c['id'], {})
                if folder: self.assertEqual(result['draft']['folder'],folder)
                if expected: self.assertIn(expected, result['draft']['title'])
                self.assertIn('fuente_titulo: ' + json.dumps(original,ensure_ascii=False),preview['markdown'])
                self.assertNotIn('orden_lectura:',preview['markdown'])
                if i == 0:
                    self.assertIn('origen: "Profesora"',preview['markdown'])
                    self.assertIn('fuente_alojamiento: "drive.google.com"',preview['markdown'])
                    self.assertNotIn('modulo_aws:',preview['markdown'])
                if i == 2: self.assertNotIn('seccion_fuente:',preview['markdown'])
                if i == 3:
                    self.assertNotIn('curso_fuente:',preview['markdown'])
                    self.assertIn('contexto_pendiente:',preview['markdown'])
                saved = self.app.save(c['id'],{})
                if folder:
                    index = (self.vault / folder / 'index.md').read_text()
                    self.assertIn(saved['relative'].removesuffix('.md'),index)
                    self.assertIn('Tabla original',index)
                    self.assertTrue(list((self.app.state/'update-backups'/c['id']).glob('*.bak')))
                other, _ = self.prepare(original,catalog,topic + ' revisado',url)
                self.assertEqual(self.app.duplicate(self.app.load(other['id'])),saved['relative'])
                with self.assertRaises(UserError): self.app.save(other['id'],{})

    def test_topic_mentions_do_not_establish_membership_and_missing_evidence_is_rejected(self):
        c = {'title':'Infraestructura', 'text':'La profesora remite al módulo 3 de AWS Cloud Foundations', 'source_context':{}}
        self.assertEqual(resolve(c),{})
        self.assertEqual(resolve(c,[{'field':'modulo_aws','value':'2','evidence':'inventado'}]),{})
        c['source_context']={'catalog':'AWS Cloud Foundations > Module 2 > Module 3'}
        self.assertNotIn('modulo_aws',resolve(c))

    def test_index_write_failure_rolls_back_note_and_retains_original(self):
        folder=self.group('teoria/AWS/02',{'origen':'AWS Academy','curso_fuente':'AWS Academy Cloud Foundations','modulo_aws':2})
        c,_=self.prepare('Module 2 - Section 3','AWS Cloud Foundations','AWS Organizations')
        index=self.vault/folder/'index.md';before=index.read_bytes()
        with patch('publication.replace_checked',side_effect=UserError('conflict')):
            with self.assertRaises(UserError): self.app.save(c['id'],{})
        self.assertEqual(index.read_bytes(),before)
        self.assertEqual(len(list((self.vault/folder).glob('*.md'))),2)

    def test_renamed_saved_note_is_found_without_history_path(self):
        c, _ = self.prepare('Introducción', '', 'Recursos lógicos')
        saved = self.app.save(c['id'], {})
        path = Path(saved['path'])
        renamed = path.with_name('Renombrada.md')
        path.rename(renamed)
        self.assertEqual(self.app.duplicate(self.app.load(c['id'])), renamed.relative_to(self.vault).as_posix())

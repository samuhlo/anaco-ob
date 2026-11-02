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
                # As in the user's vault, notes are named by their title.
                rule['filenames'] = {'apunte': '{title}.md'}
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
            ('Apartado 05', 'MP5160 > Profesora > UD01', 'Infraestructura física y recursos lógicos', professor, 'UD1 · Apartado 5: Infraestructura'),
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

    def test_titles_take_only_numbered_sections_and_never_a_long_course_name(self):
        from provenance import title
        drive = {'title':'UD02-Apartado07-8.mp4','context':'','source_context':{'resource_title':'UD02-Apartado07-8.mp4','page_title':'UD02-Apartado07-8.mp4 - Google Drive'}}
        facts = resolve(drive)
        self.assertEqual((facts['unidad_didactica'], facts['seccion_fuente']), ('UD02', '7–8'))
        self.assertEqual(title({'provenance':facts}, 'Multicloud frente a nube híbrida'), 'UD2 · Apartados 7 y 8: Multicloud frente a nube híbrida')
        # The model already wrote the unit and section: nothing is repeated.
        self.assertEqual(title({'provenance':facts}, 'UD2 · Apartados 7 y 8: multicloud'), 'UD2 · Apartados 7 y 8: multicloud')
        moodle = resolve({'title':'135_36019402_ZE3IFC005500_MP5160_A: Vídeo-UD02-Apartado6 | FP A DISTANCIA','context':'','source_context':{}})
        self.assertEqual((moodle['modulo'], moodle['unidad_didactica'], moodle['seccion_fuente']), ('MP5160', 'UD02', '6'))
        # Textual sections and model-supplied course names stay in metadata only.
        textual = {'unidad_didactica':'UD02', 'seccion_fuente':'apartados siete y ocho de los apuntes', 'curso_fuente':'Curso de especialización - Recursos y servicios en la nube.'}
        self.assertEqual(title({'provenance':textual}, 'Gobernanza híbrida'), 'UD2: Gobernanza híbrida')
        self.assertEqual(title({'provenance':{'curso_fuente':'Curso de especialización - Recursos y servicios en la nube.', 'seccion_fuente':'Vídeo-UD02-Apartado6'}}, 'Portabilidad'), 'Portabilidad')
        aws = resolve({'title':'Module 2 - Section 3','context':'','source_context':{'catalog':'AWS Academy Cloud Foundations'}})
        self.assertEqual(title({'provenance':aws}, 'AWS Organizations'), 'AWS Cloud Foundations · M02 · S03 · AWS Organizations')

    def units(self, module):
        """A module whose teacher notes live in numbered unit folders, as in the user's vault."""
        root = '07_Clases/02_Master_Nube/' + module + ' - Módulo/teoria/01_Profesora'
        unit = self.vault / root / 'UD01'
        unit.mkdir(parents=True)
        facts = {'tipo':'apunte','curso':'Master Nube','asignatura':'Módulo ' + module,'modulo':module,'origen':'Profesora de ' + module,
                 'unidad_didactica':'UD01','orden_lectura':1,'asignatura_nota':'[[' + module + ']]'}
        (unit / '01 - UD1 · Primer apartado.md').write_text('---\n' + '\n'.join(k + ': ' + json.dumps(v, ensure_ascii=False) for k, v in facts.items()) + '\n---\n# UD1 · Primer apartado\n')
        (self.vault / root / 'index.md').write_text('---\ntipo: indice\n---\n# Profesora\n')
        return root

    def course_draft(self, title, folder, intent='', topic='Nube híbrida'):
        c = self.app.stage({'kind':'video','url':'https://drive.google.com/file/d/' + title + '/view','title':title,'text':'Transcripción sobre ' + topic,
                            'source_context':{'resource_title':title}})
        result = {'title':topic,'context':'Clase','body':'Transcripción sobre ' + topic,'folder':folder,'tags':[],'relations':[]}
        with patch.object(self.app, 'codex_generate', return_value=result):
            return c, self.app.draft(c['id'], intent=intent, provider='codex')['draft']

    def test_a_new_unit_goes_next_to_the_previous_ones_with_their_metadata_and_numbering(self):
        root = self.units('MP5160')
        c, draft = self.course_draft('UD02-Apartado06.mp4', '07_Clases')
        self.assertEqual(draft['folder'], root + '/UD02')
        self.assertEqual(draft['filename'], '01 - UD2 · Apartado 6 Nube híbrida.md')
        self.assertIn(root + '/UD02', self.app.handle({'action':'review_data','id':c['id']})['folders'])
        markdown = self.app.preview(c['id'], {})['markdown']
        for line in ('curso: "Master Nube"', 'asignatura: "Módulo MP5160"', 'modulo: "MP5160"', 'origen: "Profesora de MP5160"', 'unidad_didactica: "UD02"', 'orden_lectura: 1'):
            self.assertIn(line, markdown)
        # A failed save leaves no empty unit folder behind.
        with patch('publication.replace_checked', side_effect=UserError('conflict')):
            with self.assertRaises(UserError): self.app.save(c['id'], {})
        self.assertFalse((self.vault / root / 'UD02').exists())
        saved = self.app.save(c['id'], {})
        self.assertEqual(saved['relative'], root + '/UD02/01 - UD2 · Apartado 6 Nube híbrida.md')
        _, second = self.course_draft('UD02-Apartado07.mp4', '07_Clases', topic='Multicloud')
        self.assertEqual(second['filename'], '02 - UD2 · Apartado 7 Multicloud.md')

    def test_units_of_another_course_are_not_taken_by_topic(self):
        first, second = self.units('MP5160'), self.units('MP5161')
        _, draft = self.course_draft('UD02-Apartado06.mp4', '07_Clases')
        self.assertEqual(draft['folder'], '07_Clases')
        # The user's own intent names the module.
        _, draft = self.course_draft('UD02-Apartado06.mp4', '07_Clases', intent='Apuntes de MP5161', topic='Otro tema')
        self.assertEqual(draft['folder'], second + '/UD02')
        # A folder the model chose outside the unit tree is respected.
        other = self.vault / '07_Clases/01_Habilitacion/Tema'
        other.mkdir(parents=True)
        _, draft = self.course_draft('UD02-Apartado06.mp4', '07_Clases/01_Habilitacion/Tema', topic='Tercer tema')
        self.assertEqual(draft['folder'], '07_Clases/01_Habilitacion/Tema')
        self.assertNotIn(' - ', draft['filename'][:5])
        self.assertTrue(first)

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

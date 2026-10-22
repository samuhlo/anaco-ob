import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'native'))
from conversation import STRETCH_CHARS, quote_time, stretches, source_excerpts, resolve_evidence, literal
from core import UserError
from media import Media, stamp
import test_core as core_tests

FOLDER='02_Cerebro/Tech_&_Codigo'


def segments(hours=3,step=10):
    """A long conversation: one line every few seconds; the last stretch alone talks about cryptocurrencies."""
    total=hours*3600;out=[]
    for second in range(0,total,step):
        topic='las criptomonedas y su volatilidad' if second>total-1200 else 'el ahorro a largo plazo y la inflación'
        out.append({'start':second,'text':f'En el minuto {second//60} seguimos hablando de {topic}, con ejemplos concretos de familias que reparten su sueldo entre gastos fijos y un fondo de emergencia.'})
    return out


def answer(**extra):
    return {'title':'Conversación sobre dinero','context':'Ahorro e inversión','body':'## Resumen\n\nUna conversación larga sobre dinero.','folder':FOLDER,
            'tags':['economia'],'relations':[],'image_captions':[],'note_type':'fuente_externa','strategy':'source','source_format':'podcast',
            'rationale':'Una fuente','notes':[],**extra}


class StretchTest(unittest.TestCase):
    def test_original_excerpts_are_bounded_verbatim_and_include_the_end(self):
        text='\n'.join(f'[{stamp(s)}] '+'palabra '*30 for s in range(0,10800,10))+' ÚLTIMA_IDEA'
        excerpts=source_excerpts(text)
        self.assertEqual(len(excerpts),128)
        self.assertEqual(len({v['id'] for v in excerpts}),128)
        self.assertTrue(all(15<=len(v['text'])<=640 and v['text'] in text for v in excerpts))
        self.assertEqual(excerpts[0]['start'],'00:00');self.assertIn('ÚLTIMA_IDEA',excerpts[-1]['text'])

    def test_evidence_ids_resolve_in_children_and_relations_without_guessing_unknown_ids(self):
        excerpts=[{'id':'source-0001','text':'Una frase literal de la fuente original.'}]
        result={'relations':[{'source_evidence':'source-0001'}],
                'notes':[{'source_evidence':'source-0001','relations':[{'source_evidence':'source-0001'}]},
                         {'source_evidence':'source-9999','relations':[]}]}
        resolve_evidence(result,excerpts)
        self.assertEqual(result['relations'][0]['source_evidence'],excerpts[0]['text'])
        self.assertEqual(result['notes'][0]['source_evidence'],excerpts[0]['text'])
        self.assertEqual(result['notes'][0]['relations'][0]['source_evidence'],excerpts[0]['text'])
        self.assertEqual(result['notes'][1]['source_evidence'],'source-9999')

    def test_stretches_cover_every_line_once_and_start_at_chapters(self):
        lines=[f'[{stamp(s)}] '+'palabra '*30 for s in range(0,7200,10)]
        lines.insert(400,'[Capítulo 66:40] Segunda parte')
        text='\n'.join(lines);parts=stretches(text)
        self.assertGreater(len(parts),1);self.assertEqual('\n'.join(parts),text)
        self.assertTrue(all(len(p)<=STRETCH_CHARS for p in parts))
        self.assertTrue(any(p.startswith('[Capítulo 66:40]') for p in parts))

    def test_quotes_are_found_word_by_word_across_caption_lines(self):
        text='[12:30] no vendáis vuestra\n[12:32] vida por dinero porque\n[12:35] luego no vuelve'
        self.assertEqual(quote_time(text,'«No vendáis vuestra vida por dinero»'),750)
        self.assertEqual(quote_time(text,'vida por dinero, porque luego no vuelve.'),752)
        self.assertIsNone(quote_time(text,'No vendáis vuestra vida por nada'))
        self.assertIsNone(quote_time(text,'vida por'))


class LongConversationTest(unittest.TestCase):
    setUp=core_tests.CoreTest.setUp
    tearDown=core_tests.CoreTest.tearDown

    def long_capture(self):
        return Media(self.app).transcript_capture(segments(),'Tres horas de economía','https://www.youtube.com/watch?v=abcdefghijk','Subtítulos de la plataforma',metadata={'duration_seconds':10800})

    def fake(self,calls):
        def ai(prompt,spec,*args):
            if 'body' not in spec['properties']:
                calls.append('stretch');part=json.loads(prompt.split('\n\n',1)[1])['transcript']
                line=' '.join(part.splitlines()[-1].split('] ',1)[1].split()[:12])
                topic='criptomonedas' if 'criptomonedas' in part else 'ahorro'
                return {'summary':f'[00:00] En este tramo se habla de {topic}.','quotes':[{'text':line,'speaker':''},{'text':'Una frase que nadie ha dicho en el programa entero.','speaker':''}]}
            calls.append(prompt);return answer()
        return ai

    def test_three_hours_are_read_by_stretches_and_the_synthesis_sees_the_end(self):
        c=self.long_capture()
        self.assertEqual(c['warnings'],[]);self.assertTrue(self.app.load(c['id'])['text'].endswith('fondo de emergencia.'))
        calls=[];events=[];self.app.progress=events.append
        with patch.object(self.app,'codex_json',side_effect=self.fake(calls)):draft=self.app.draft(c['id'],provider='codex')
        parts=stretches(self.app.load(c['id'])['text'])
        self.assertEqual(calls.count('stretch'),len(parts));self.assertGreater(len(parts),4)
        synthesis=calls[-1]
        self.assertIn('criptomonedas',synthesis)
        self.assertIn('[02:59:00] «En el minuto 179 seguimos hablando de las criptomonedas y su volatilidad,»',synthesis);self.assertNotIn('nadie ha dicho',synthesis)
        self.assertIn(str(len(parts)),draft['capture']['media']['coverage'])
        reading=[p for p in events if p['stage']=='reading']
        self.assertEqual([p['completed'] for p in reading],list(range(len(parts)+1)))
        self.assertTrue(all(p['total']==len(parts) and p['unit']=='stretches' for p in reading))
        self.assertEqual(events[-1]['stage'],'synthesis');self.assertNotIn('completed',events[-1])

    def test_a_retry_reuses_the_stretches_already_read(self):
        c=self.long_capture();calls=[]
        with patch.object(self.app,'codex_json',side_effect=self.fake(calls)):self.app.draft(c['id'],provider='codex')
        again=[];events=[];self.app.progress=events.append
        with patch.object(self.app,'codex_json',side_effect=self.fake(again)):self.app.draft(c['id'],provider='codex')
        self.assertNotIn('stretch',again);self.assertEqual(len(again),1)
        total=len(stretches(self.app.load(c['id'])['text']))
        self.assertEqual(events[-2]['completed'],total);self.assertEqual(events[-1]['stage'],'synthesis')

    def test_failed_stretch_is_not_counted_as_complete(self):
        c=self.long_capture();events=[];self.app.progress=events.append;calls=[]
        fake=self.fake(calls)
        def fail(prompt,spec,*args):
            if len(calls)==1:raise RuntimeError('interrupted')
            return fake(prompt,spec,*args)
        with patch.object(self.app,'codex_json',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'interrupted'):self.app.draft(c['id'],provider='codex')
        completed = [p['completed'] for p in events]
        self.assertEqual(completed, list(range(len(completed))))
        self.assertLess(completed[-1], len(stretches(self.app.load(c['id'])['text'])))
        self.assertTrue(all(p['stage'] == 'reading' for p in events))

    def test_a_short_transcript_keeps_a_single_call(self):
        c=Media(self.app).transcript_capture(segments(hours=1,step=60),'Una hora','https://www.youtube.com/watch?v=abcdefghijk','Subtítulos')
        calls=[]
        with patch.object(self.app,'codex_json',side_effect=self.fake(calls)):self.app.draft(c['id'],provider='codex')
        self.assertEqual(len(calls),1);self.assertNotEqual(calls[0],'stretch')

    def test_reasoning_change_does_not_reuse_lower_quality_stretch_summaries(self):
        c=self.long_capture();calls=[]
        self.app.set_config({'reasoning_effort':'low'})
        with patch.object(self.app,'codex_json',side_effect=self.fake(calls)):self.app.draft(c['id'],provider='codex')
        self.app.set_config({'reasoning_effort':'medium'});again=[]
        with patch.object(self.app,'codex_json',side_effect=self.fake(again)):self.app.draft(c['id'],provider='codex')
        self.assertEqual(again.count('stretch'),calls.count('stretch'))

    def test_two_readers_keep_chronology_and_use_luna_before_sol(self):
        c = self.long_capture()
        parts = stretches(self.app.load(c['id'])['text'])
        rendezvous = threading.Barrier(2)
        lock = threading.Lock()
        main = threading.get_ident()
        active = maximum = 0
        calls, events, synthesis = [], [], []
        self.app.progress = lambda value: events.append((threading.get_ident(), value))
        def ai(prompt, spec, model=None, *args):
            nonlocal active, maximum
            if 'body' in spec['properties']:
                self.assertEqual(model, 'gpt-6.1-sol')
                synthesis.append(json.loads(prompt[prompt.index('{"profile":'):])['capture']['text'])
                return answer(_model=model)
            data = json.loads(prompt.split('\n\n', 1)[1])
            index = parts.index(data['transcript'])
            with lock:
                active += 1
                maximum = max(maximum, active)
                calls.append(model)
            try:
                if index < 2:
                    rendezvous.wait(timeout=3)
                return {'summary': f'READING_{index}', 'quotes': [], '_model': model}
            finally:
                with lock:
                    active -= 1
        with patch.object(self.app, 'codex_json', side_effect=ai):
            self.app.draft(c['id'], provider='codex')
        self.assertEqual(maximum, 2)
        self.assertEqual(calls, ['gpt-6-luna'] * len(parts))
        self.assertEqual(sorted(range(len(parts)), key=lambda i: synthesis[0].index(f'READING_{i}')), list(range(len(parts))))
        self.assertTrue(all(thread == main for thread, _ in events))
        self.assertEqual(self.app.load(c['id'])['media']['reading_models'], ['gpt-6-luna', 'gpt-6.1-sol'])

    def test_new_capture_and_new_final_model_reuse_the_same_readings(self):
        first = self.long_capture()
        calls = []
        with patch.object(self.app, 'codex_json', side_effect=self.fake(calls)):
            self.app.draft(first['id'], provider='codex')
        second = self.long_capture()
        self.assertNotEqual(first['id'], second['id'])
        self.app.set_config({'model': 'another-final-model'})
        again = []
        with patch.object(self.app, 'codex_json', side_effect=self.fake(again)):
            self.app.draft(second['id'], provider='codex')
        self.assertEqual(len(again), 1)
        self.assertNotIn('stretch', again)

    def test_reader_changes_invalidate_cache_and_corrupt_entries_are_repaired(self):
        c = self.long_capture()
        calls = []
        with patch.object(self.app, 'codex_json', side_effect=self.fake(calls)):
            self.app.draft(c['id'], provider='codex')
        for path in (self.app.state / 'stretches').rglob('*.json'):
            path.write_text('{broken')
        again = []
        with patch.object(self.app, 'codex_json', side_effect=self.fake(again)):
            self.app.draft(c['id'], provider='codex')
        self.assertEqual(again.count('stretch'), calls.count('stretch'))
        self.app.set_config({'reading_model': 'another-reader'})
        changed = []
        with patch.object(self.app, 'codex_json', side_effect=self.fake(changed)):
            self.app.draft(c['id'], provider='codex')
        self.assertEqual(changed.count('stretch'), calls.count('stretch'))

    def test_failure_preserves_successful_readings(self):
        c = self.long_capture()
        parts = stretches(self.app.load(c['id'])['text'])
        sibling_running = threading.Event()
        finished = threading.Event()
        def ai(prompt, spec, model=None, *args):
            part = json.loads(prompt.split('\n\n', 1)[1])['transcript']
            index = parts.index(part)
            if index == 0:
                sibling_running.wait(3)
                return {'summary': 'Primer tramo conservado.', 'quotes': []}
            if index == 1:
                sibling_running.set()
                # Wait for the next task to start, so the first result is cached.
                finished.wait(3)
                raise RuntimeError('reader failed')
            finished.set()
            return {'summary': 'Otro tramo completo.', 'quotes': []}
        with patch.object(self.app, 'codex_json', side_effect=ai):
            with self.assertRaisesRegex(RuntimeError, 'reader failed'):
                self.app.draft(c['id'], provider='codex')
        cached = list((self.app.state / 'stretches' / 'shared').glob('*.json'))
        self.assertTrue(any(json.loads(p.read_text())['summary'] == 'Primer tramo conservado.' for p in cached))
        self.assertEqual(self.app.load(c['id'])['status'], 'pending')

    def test_failed_worker_stops_the_other_reader_without_waiting_for_its_timeout(self):
        c = self.long_capture()
        first = stretches(self.app.load(c['id'])['text'])[0]
        running, stopped = threading.Event(), threading.Event()
        def ai(worker, prompt, spec, model=None, *args):
            part = json.loads(prompt.split('\n\n', 1)[1])['transcript']
            if part == first:
                self.assertTrue(running.wait(3))
                raise UserError('reader failed')
            running.set()
            try:
                for _ in range(300):
                    worker.check_cancel()
                    stopped.wait(.01)
                self.fail('The other reader was not stopped')
            except RuntimeError:
                stopped.set()
                raise
        with patch('core.App.codex_json', new=ai):
            with self.assertRaisesRegex(UserError, 'reader failed'):
                self.app.draft(c['id'], provider='codex')
        self.assertTrue(stopped.is_set())

    def test_api_readings_do_not_send_a_codex_model_to_another_provider(self):
        self.app.set_config({'provider': 'openai', 'api_model': 'local-reader', 'api_base': 'http://localhost:11434/v1'})
        c = self.long_capture()
        calls = []
        def api(cfg, prompt, spec, images=None):
            self.assertEqual(cfg['api_model'], 'local-reader')
            return self.fake(calls)(prompt, spec)
        with patch('ai.openai_json', side_effect=api):
            self.app.draft(c['id'], provider='openai')
        self.assertGreater(calls.count('stretch'), 1)

    def test_detailed_stretch_readings_reach_synthesis_without_preview_truncation(self):
        c=self.long_capture();calls=[]
        def ai(prompt,spec,*args):
            if 'body' not in spec['properties']:
                part=json.loads(prompt.split('\n\n',1)[1])['transcript']
                return {'summary':'Detalle conservado. '*1900+('ÚLTIMO_TEMA_CRIPTOMONEDAS' if 'criptomonedas' in part else 'OTRO_TEMA'),'quotes':[]}
            calls.append(prompt);return answer()
        with patch.object(self.app,'codex_json',side_effect=ai):self.app.draft(c['id'],provider='codex')
        self.assertIn('ÚLTIMO_TEMA_CRIPTOMONEDAS',calls[-1])
        self.assertGreater(len(calls[-1]),160000)

    def linked_answer(self,prompt,spec,invalid=None):
        capture=json.loads(prompt[prompt.index('{"profile":'):])['capture']
        excerpts=capture['source_excerpts'];ids=[v['id'] for v in excerpts]
        child_spec=spec['properties']['notes']['items']['properties']
        self.assertEqual(child_spec['source_evidence']['enum'],ids)
        self.assertEqual(child_spec['relations']['items']['properties']['source_evidence']['enum'],ids)
        self.assertEqual(spec['properties']['relations']['items']['properties']['source_evidence']['enum'],ids)
        common={'folder':FOLDER,'context':'Aprendizaje','note_type':'nota_atomica','tags':[],'relations':[],'pages':[],'images':[],'links':[]}
        last=next(v for v in reversed(excerpts) if 'criptomonedas' in v['text'])
        return answer(strategy='collection',notes=[
            {**common,'id':'tema-ahorro','title':'Ahorrar con criterio','body':'Explicación y aplicación del ahorro.','source_evidence':invalid or excerpts[0]['id']},
            {**common,'id':'tema-criptomonedas','title':'Entender la volatilidad','body':'Explicación y aplicación de la volatilidad.','source_evidence':last['id']}])

    def test_long_podcast_linked_notes_resolve_original_evidence_and_save(self):
        c=self.long_capture();calls=[];read=self.fake(calls)
        def ai(prompt,spec,*args):
            return self.linked_answer(prompt,spec) if 'body' in spec['properties'] else read(prompt,spec,*args)
        with patch.object(self.app,'codex_json',side_effect=ai):self.app.draft(c['id'],provider='codex',note_structure='linked')
        stored=self.app.load(c['id'])
        self.assertNotIn('source_excerpts',stored)
        for note in stored['bundle']['notes']:
            self.assertIn(note['source_evidence'],stored['text'])
            self.assertFalse(note['source_evidence'].startswith('source-'))
        self.assertIn('criptomonedas',stored['bundle']['notes'][-1]['source_evidence'])
        saved=self.app.save(c['id'],{});self.assertEqual(saved['count'],3)
        for relative in saved['paths']:self.assertTrue((self.vault/relative).is_file())

    def test_synthesis_paraphrases_and_invented_ids_still_cannot_back_derived_notes(self):
        for invalid in ['source-9999','Una síntesis inventada sobre la distribución óptima del patrimonio.']:
            c=self.long_capture();calls=[];read=self.fake(calls)
            self.assertFalse(literal(self.app.load(c['id'])['text'],invalid))
            def ai(prompt,spec,*args):
                return self.linked_answer(prompt,spec,invalid) if 'body' in spec['properties'] else read(prompt,spec,*args)
            with patch.object(self.app,'codex_json',side_effect=ai):
                with self.assertRaisesRegex(UserError,'referencia verificable'):self.app.draft(c['id'],provider='codex',note_structure='linked')
            self.assertEqual(self.app.load(c['id'])['status'],'pending')


class ConversationNoteTest(unittest.TestCase):
    setUp=core_tests.CoreTest.setUp
    tearDown=core_tests.CoreTest.tearDown
    LINES=[{'start':5,'text':'Bienvenido Emilio Duró a Tengo un Plan'},{'start':750,'text':'no vendáis vuestra'},{'start':752,'text':'vida por dinero porque'},{'start':755,'text':'luego no vuelve'}]

    def podcast(self):
        c=Media(self.app).transcript_capture(self.LINES,'Emilio Duró: sentido y afecto','https://www.youtube.com/watch?v=abcdefghijk','Subtítulos de la plataforma',metadata={'duration_seconds':3600},author='Tengo un Plan')
        return c

    def draft(self,c,result,conversation=None):
        prompts=[]
        def ai(prompt,spec,*args):prompts.append(prompt);return result
        with patch.object(self.app,'codex_json',side_effect=ai):draft=self.app.draft(c['id'],provider='codex',conversation=conversation)['draft']
        return draft,prompts[-1]

    def conversation_answer(self):
        return answer(body='## Temas tratados\n\n- [12:30] Dinero y sentido.\n\n%%citas%%\n\n## Qué me llevo\n\n- Revisar si cambio tiempo por dinero.',
                      quotes=[{'text':'No vendáis vuestra vida por dinero.','speaker':'Emilio Duró'},{'text':'El dinero lo es todo en la vida.','speaker':''}],
                      author='Emilio Duró / Tengo un Plan / Uri Sabat')

    def test_forced_conversation_places_only_literal_quotes_with_their_minute(self):
        c=self.podcast();draft,prompt=self.draft(c,self.conversation_answer(),'on')
        self.assertIn('Esta captura es un podcast o una entrevista',prompt)
        body=draft['body']
        self.assertIn('## Citas destacadas\n\n> «No vendáis vuestra vida por dinero.» — Emilio Duró · [12:30]',body)
        self.assertLess(body.index('Citas destacadas'),body.index('Qué me llevo'));self.assertNotIn('%%citas%%',body)
        self.assertNotIn('lo es todo',body);self.assertEqual(draft['rationale'],'Una fuente. Se ha descartado una cita que no aparece palabra por palabra en la transcripción.')
        self.assertEqual(draft['author'],'Emilio Duró / Tengo un Plan')
        markdown=self.app.preview(c['id'],{})['markdown']
        self.assertIn('· [12:30](https://www.youtube.com/watch?v=abcdefghijk&t=750s)',markdown)
        self.assertIn('formato: "podcast"',markdown)

    def test_automatic_mode_lets_the_model_decide_and_a_plain_video_gets_no_quotes(self):
        c=self.podcast();result=self.conversation_answer();result['source_format']='video'
        draft,prompt=self.draft(c,result)
        self.assertIn('Si el vídeo es una conversación',prompt)
        self.assertNotIn('Citas destacadas',draft['body']);self.assertNotIn('%%citas%%',draft['body'])
        self.assertEqual(draft.get('author',''),'')

    def test_a_video_can_be_prepared_again_without_the_conversation_form(self):
        c=self.podcast();self.draft(c,self.conversation_answer(),'on')
        result=answer(source_format='video',quotes=[],author='')
        draft,prompt=self.draft(c,result,'off')
        self.assertIn('No uses la forma de conversación',prompt);self.assertEqual(self.app.load(c['id'])['conversation'],'off')
        self.assertNotIn('Citas destacadas',draft['body'])

    def test_articles_never_receive_conversation_guidance(self):
        c=self.app.stage({'kind':'article','url':'https://example.org/a','title':'Artículo','text':'Un artículo sobre ahorro y presupuesto familiar con ejemplos.'})
        _,prompt=self.draft(c,answer(source_format='articulo',quotes=[],author=''))
        self.assertNotIn('conversación',prompt.split('\n\n',1)[0])


class PlaceQuotesTest(unittest.TestCase):
    SECTION='## Citas destacadas\n\n> «x» · [00:01]'

    def test_the_mark_written_as_a_heading_or_under_its_own_heading_leaves_one_heading(self):
        from conversation import place
        for body in ('## Ideas\n\nuna\n\n## %%citas%%\n\n## Qué me llevo\n\n- algo','## Ideas\n\nuna\n\n## Citas\n\n%%citas%%\n\n## Qué me llevo\n\n- algo',
                     '## Ideas\n\nuna\n\n- %%citas%%\n\n## Qué me llevo\n\n- algo'):
            with self.subTest(body):
                self.assertEqual(place(body,self.SECTION),'## Ideas\n\nuna\n\n'+self.SECTION+'\n\n## Qué me llevo\n\n- algo')

    def test_a_heading_with_its_own_text_before_the_mark_is_kept(self):
        from conversation import place
        self.assertEqual(place('## Ideas\n\nuna\n\n%%citas%%',self.SECTION),'## Ideas\n\nuna\n\n'+self.SECTION)

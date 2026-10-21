import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'native'))
from conversation import STRETCH_CHARS, quote_time, stretches
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
        calls=[]
        with patch.object(self.app,'codex_json',side_effect=self.fake(calls)):draft=self.app.draft(c['id'],provider='codex')
        parts=stretches(self.app.load(c['id'])['text'])
        self.assertEqual(calls.count('stretch'),len(parts));self.assertGreater(len(parts),4)
        synthesis=calls[-1]
        self.assertIn('criptomonedas',synthesis)
        self.assertIn('[02:59:00] «En el minuto 179 seguimos hablando de las criptomonedas y su volatilidad,»',synthesis);self.assertNotIn('nadie ha dicho',synthesis)
        self.assertIn(str(len(parts)),draft['capture']['media']['coverage'])

    def test_a_retry_reuses_the_stretches_already_read(self):
        c=self.long_capture();calls=[]
        with patch.object(self.app,'codex_json',side_effect=self.fake(calls)):self.app.draft(c['id'],provider='codex')
        again=[]
        with patch.object(self.app,'codex_json',side_effect=self.fake(again)):self.app.draft(c['id'],provider='codex')
        self.assertNotIn('stretch',again);self.assertEqual(len(again),1)

    def test_a_short_transcript_keeps_a_single_call(self):
        c=Media(self.app).transcript_capture(segments(hours=1,step=60),'Una hora','https://www.youtube.com/watch?v=abcdefghijk','Subtítulos')
        calls=[]
        with patch.object(self.app,'codex_json',side_effect=self.fake(calls)):self.app.draft(c['id'],provider='codex')
        self.assertEqual(len(calls),1);self.assertNotEqual(calls[0],'stretch')


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

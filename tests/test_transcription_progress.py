import json
import sys
import unittest
import contextlib
import io
import runpy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'native'))
from media import run_progress
from core import UserError

class TranscriptionProgressTest(unittest.TestCase):
    def test_worker_reaches_full_duration_after_processing_trailing_silence(self):
        segment=SimpleNamespace(start=0,end=50,text='Audio fixture')
        model=SimpleNamespace(transcribe=lambda *args,**kwargs:(iter([segment]),SimpleNamespace(duration=60,language='es')))
        output=io.StringIO()
        with patch.dict(sys.modules,{'faster_whisper':SimpleNamespace(WhisperModel=lambda *args,**kwargs:model)}),patch.object(sys,'argv',['transcribe.py','audio.wav','--cache','/tmp/anaco-test-cache','--progress']),contextlib.redirect_stdout(output):
            runpy.run_path(str(Path(__file__).resolve().parents[1]/'native/transcribe.py'),run_name='__main__')
        events=[json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(events[-2]['processed_seconds'],60);self.assertEqual(events[-2]['total_seconds'],60)
        self.assertEqual(events[-1]['event'],'result')

    def test_progress_is_forwarded_without_transcript_text_and_result_is_kept(self):
        events=[{'event':'progress','stage':'transcribe','message':'Transcribiendo','processed_seconds':12,'total_seconds':60,'text':'PRIVATE AUDIO'},
                {'event':'result','result':{'language':'es','segments':[{'start':0,'end':12,'text':'Contenido privado'}]}}]
        command=[sys.executable,'-c','import sys;sys.stdout.write('+repr(''.join(json.dumps(v)+'\n' for v in events))+')']
        received=[];result=run_progress(command,received.append)
        self.assertEqual(received[0]['processed_seconds'],12);self.assertNotIn('text',received[0]);self.assertEqual(result,events[-1]['result'])

    def test_failed_or_missing_result_does_not_claim_a_completed_transcription(self):
        for code in ('print("invalid")','print(\'{"event":"progress","stage":"model"}\')','raise SystemExit(1)'):
            with self.assertRaises(UserError):run_progress([sys.executable,'-c',code],lambda value:None)

    def test_timeout_ends_worker_instead_of_waiting_indefinitely(self):
        with self.assertRaisesRegex(UserError,'tiempo máximo'):run_progress([sys.executable,'-c','import time;time.sleep(30)'],lambda value:None,timeout=.1)

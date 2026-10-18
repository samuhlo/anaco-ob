import json
import sys
import unittest
from media import run_progress
from core import UserError

class TranscriptionProgressTest(unittest.TestCase):
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

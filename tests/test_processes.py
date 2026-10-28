"""Run these on Linux, macOS and Windows; no media engine is required."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'native'))
from jobs import Cancelled, running, run_command
from media import run_progress


class ProcessLifecycleTest(unittest.TestCase):
    def test_status_queries_do_not_terminate_a_live_process(self):
        with subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']) as child:
            try:
                for _ in range(3):
                    self.assertTrue(running({'status': 'running', 'pid': child.pid}))
                time.sleep(.1)
                self.assertIsNone(child.poll())
            finally:
                child.kill()
                child.wait()
        self.assertFalse(running({'status': 'running', 'pid': child.pid}))

    def test_a_reused_pid_does_not_make_an_old_job_live(self):
        self.assertFalse(running({'status': 'running', 'pid': os.getpid(),
                                  'process_identity': 'a different process creation time'}))

    def test_large_input_and_both_output_pipes_complete(self):
        code = 'import sys; data=sys.stdin.read(); sys.stderr.write("e"*200000); sys.stdout.write(data)'
        result = run_command([sys.executable, '-c', code], lambda: None,
                             input='x' * 200000, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, 'x' * 200000)
        self.assertEqual(len(result.stderr), 200000)

    def test_timeout_and_immediate_cancellation_keep_the_original_error(self):
        command = [sys.executable, '-c', 'import time; time.sleep(30)']
        with self.assertRaises(subprocess.TimeoutExpired):
            run_command(command, lambda: None, timeout=.2)
        def cancel():
            raise Cancelled()
        with self.assertRaises(Cancelled):
            run_command(command, cancel)

    def tree(self, parent_exits=False, progress=False):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            heartbeat, pidfile = folder / 'heartbeat', folder / 'pid'
            leaf = "import time\nfrom pathlib import Path\np=Path(" + repr(str(heartbeat)) + ")\nwhile True:\n p.write_text(str(time.time_ns()))\n time.sleep(.03)"
            code = ('import subprocess,sys,time\nfrom pathlib import Path\n'
                    f'child=subprocess.Popen([sys.executable,"-c",{leaf!r}])\n'
                    f'Path({str(pidfile)!r}).write_text(str(child.pid))\n'
                    + ('' if parent_exits else 'time.sleep(30)\n'))
            ready_at = None
            deadline = time.monotonic() + 10
            def check():
                nonlocal ready_at
                if heartbeat.exists() and pidfile.exists():
                    ready_at = ready_at or time.monotonic()
                    if time.monotonic() - ready_at > .3:
                        raise Cancelled()
                if time.monotonic() > deadline:
                    raise AssertionError('The child process did not start')
            try:
                with self.assertRaises(Cancelled):
                    if progress:
                        run_progress([sys.executable, '-c', code], lambda _: None, check=check)
                    else:
                        run_command([sys.executable, '-c', code], check)
                before = heartbeat.read_bytes()
                time.sleep(.2)
                self.assertEqual(heartbeat.read_bytes(), before, 'Descendant survived cancellation')
            finally:
                if pidfile.exists():
                    pid = int(pidfile.read_text())
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except (ProcessLookupError, OSError):
                        pass

    def test_cancellation_terminates_descendants(self):
        self.tree()

    def test_cancellation_terminates_descendants_after_parent_exits(self):
        self.tree(parent_exits=True)

    def test_progress_cancellation_terminates_descendants(self):
        self.tree(progress=True)

    def test_jsonl_progress_works_with_split_utf8_and_without_final_newline(self):
        events = [{'event': 'progress', 'stage': 'transcribe', 'message': 'Señal', 'text': 'PRIVATE'},
                  {'event': 'result', 'result': {'segments': [{'text': 'Una señal'}]}}]
        raw = '\n'.join(json.dumps(e, ensure_ascii=False) for e in events).encode()
        code = 'import os\nfor byte in ' + repr(raw) + ': os.write(1, bytes([byte]))'
        updates = []
        result = run_progress([sys.executable, '-c', code], updates.append)
        self.assertEqual(result, events[-1]['result'])
        self.assertNotIn('text', updates[0])

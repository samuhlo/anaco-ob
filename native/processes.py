"""Portable ownership of a subprocess tree and non-destructive PID queries."""
import os
from pathlib import Path
import signal
import subprocess
import sys


def process_info(pid):
    if type(pid) is not int or pid <= 0:
        return False, None
    if os.name == 'nt':
        from windows_processes import process_info as windows_info
        return windows_info(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False, None
    except PermissionError:
        return True, None
    except (OSError, ValueError, OverflowError):
        return False, None
    try:
        if sys.platform.startswith('linux'):
            fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
            if fields[0] in ('Z', 'X'):
                return False, None
            boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            return True, 'linux:' + boot + ':' + fields[19]
        result = subprocess.run(['ps', '-p', str(pid), '-o', 'lstart='],
                                capture_output=True, text=True, timeout=2)
        stamp = result.stdout.strip()
        return True, 'posix:' + stamp if result.returncode == 0 and stamp else None
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return True, None


class ManagedProcess:
    """Own every descendant until close, even when its original parent exits."""
    def __init__(self, command, **kwargs):
        self.job = None
        self.process = None
        self.stopped = False
        try:
            if os.name == 'nt':
                from windows_processes import ProcessJob
                self.job = ProcessJob()
                kwargs['creationflags'] = kwargs.get('creationflags', 0) | 0x4  # CREATE_SUSPENDED
            else:
                kwargs['start_new_session'] = True
            self.process = subprocess.Popen(command, **kwargs)
            if self.job:
                self.job.attach_and_resume(self.process)
        except BaseException:
            self.stop()
            self.close_pipes()
            raise

    def stop(self):
        if self.stopped:
            return
        self.stopped = True
        if self.job:
            self.job.close()
            self.job = None
        elif self.process and os.name != 'nt':
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except PermissionError:
                # macOS can return EPERM for an already exited process group.
                # Reap the child to distinguish that race from a live process
                # we genuinely cannot terminate.
                if self.process.poll() is None:
                    raise
        if self.process:
            # Also covers failure to assign a suspended Windows process.
            if self.process.poll() is None:
                self.process.kill()
            self.process.wait()

    def close_pipes(self):
        if self.process:
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                if stream:
                    stream.close()

    def __enter__(self):
        return self.process

    def __exit__(self, *args):
        self.stop()
        self.close_pipes()

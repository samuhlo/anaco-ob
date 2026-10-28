"""Win32 process queries and job ownership; imported only on Windows."""
import ctypes
from ctypes import wintypes as w

kernel = ctypes.WinDLL('kernel32', use_last_error=True)


def bind(name, args, result):
    function = getattr(kernel, name)
    function.argtypes, function.restype = args, result
    return function


close_handle = bind('CloseHandle', [w.HANDLE], w.BOOL)
open_process = bind('OpenProcess', [w.DWORD, w.BOOL, w.DWORD], w.HANDLE)
wait = bind('WaitForSingleObject', [w.HANDLE, w.DWORD], w.DWORD)
get_times = bind('GetProcessTimes', [w.HANDLE] + [ctypes.POINTER(w.FILETIME)] * 4, w.BOOL)
create_job = bind('CreateJobObjectW', [ctypes.c_void_p, w.LPCWSTR], w.HANDLE)
set_job = bind('SetInformationJobObject', [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL)
assign_job = bind('AssignProcessToJobObject', [w.HANDLE, w.HANDLE], w.BOOL)


class BasicLimits(ctypes.Structure):
    _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                ('flags', w.DWORD), ('minimum_working_set', ctypes.c_size_t),
                ('maximum_working_set', ctypes.c_size_t), ('active_processes', w.DWORD),
                ('affinity', ctypes.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]


class IOCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in
                ('read_ops', 'write_ops', 'other_ops', 'read_bytes', 'write_bytes', 'other_bytes')]


class ExtendedLimits(ctypes.Structure):
    _fields_ = [('basic', BasicLimits), ('io', IOCounters),
                ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t),
                ('peak_process_memory', ctypes.c_size_t), ('peak_job_memory', ctypes.c_size_t)]


class ThreadEntry(ctypes.Structure):
    _fields_ = [('size', w.DWORD), ('usage', w.DWORD), ('thread_id', w.DWORD),
                ('process_id', w.DWORD), ('priority', w.LONG), ('delta', w.LONG), ('flags', w.DWORD)]


snapshot_threads = bind('CreateToolhelp32Snapshot', [w.DWORD, w.DWORD], w.HANDLE)
thread_first = bind('Thread32First', [w.HANDLE, ctypes.POINTER(ThreadEntry)], w.BOOL)
thread_next = bind('Thread32Next', [w.HANDLE, ctypes.POINTER(ThreadEntry)], w.BOOL)
open_thread = bind('OpenThread', [w.DWORD, w.BOOL, w.DWORD], w.HANDLE)
resume_thread = bind('ResumeThread', [w.HANDLE], w.DWORD)


def process_info(pid):
    """Query without sending a signal. Access denied remains conservatively live."""
    if pid > 0xffffffff:
        return False, None
    handle = open_process(0x1000 | 0x100000, False, pid)  # query limited + synchronize
    if not handle:
        return ctypes.get_last_error() == 5, None
    try:
        status = wait(handle, 0)
        if status == 0:
            return False, None
        if status != 258:  # WAIT_TIMEOUT: still running
            raise ctypes.WinError(ctypes.get_last_error())
        creation, exit_time, system, user = (w.FILETIME() for _ in range(4))
        if not get_times(handle, ctypes.byref(creation), ctypes.byref(exit_time),
                         ctypes.byref(system), ctypes.byref(user)):
            return True, None
        return True, f'win:{creation.dwHighDateTime:08x}{creation.dwLowDateTime:08x}'
    finally:
        close_handle(handle)


class ProcessJob:
    def __init__(self):
        self.handle = create_job(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not set_job(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def attach_and_resume(self, process):
        # Popen owns the process handle. CREATE_SUSPENDED prevents the program
        # from spawning descendants before assignment to this job.
        if not assign_job(self.handle, int(process._handle)):
            raise ctypes.WinError(ctypes.get_last_error())
        snapshot = snapshot_threads(0x4, 0)  # TH32CS_SNAPTHREAD
        if snapshot == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        resumed = False
        try:
            entry = ThreadEntry()
            entry.size = ctypes.sizeof(entry)
            available = thread_first(snapshot, ctypes.byref(entry))
            while available:
                if entry.process_id == process.pid:
                    thread = open_thread(0x2, False, entry.thread_id)  # THREAD_SUSPEND_RESUME
                    if not thread:
                        raise ctypes.WinError(ctypes.get_last_error())
                    try:
                        previous = resume_thread(thread)
                        if previous == 0xffffffff:
                            raise ctypes.WinError(ctypes.get_last_error())
                        resumed = resumed or previous == 1
                    finally:
                        close_handle(thread)
                    if resumed:
                        break
                entry.size = ctypes.sizeof(entry)
                available = thread_next(snapshot, ctypes.byref(entry))
            if not resumed:
                raise OSError('The suspended process could not be resumed')
        finally:
            close_handle(snapshot)

    def close(self):
        if self.handle:
            close_handle(self.handle)
            self.handle = None

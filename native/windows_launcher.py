"""Build a small native Windows entry point; no shell participates in runtime IPC."""
import base64
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
from processes import ManagedProcess


SOURCE = r'''
using System;
using System.Text;
using System.Runtime.InteropServices;

public static class AnacoNativeHost {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct StartupInfo {
        public int size;
        public string reserved, desktop, title;
        public int x, y, width, height, charsX, charsY, fill, flags;
        public short show, reservedSize;
        public IntPtr reservedData, input, output, error;
    }
    [StructLayout(LayoutKind.Sequential)]
    private struct ProcessInfo {
        public IntPtr process, thread;
        public uint processId, threadId;
    }
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool CreateProcess(string application, StringBuilder command,
        IntPtr processAttributes, IntPtr threadAttributes, bool inheritHandles, uint flags,
        IntPtr environment, string directory, ref StartupInfo startup, out ProcessInfo process);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr GetStdHandle(int which);
    [DllImport("kernel32.dll")]
    private static extern IntPtr GetCurrentProcess();
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool DuplicateHandle(IntPtr owner, IntPtr source, IntPtr target,
        out IntPtr duplicate, uint access, bool inherit, uint options);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr CreateFile(string path, uint access, uint sharing,
        IntPtr attributes, uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll")]
    private static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern uint WaitForSingleObject(IntPtr handle, uint timeout);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetExitCodeProcess(IntPtr handle, out uint code);

    private static IntPtr InheritableStandardHandle(int which) {
        IntPtr source = GetStdHandle(which);
        bool temporary = false;
        if (source == IntPtr.Zero || source == new IntPtr(-1)) {
            if (which != -12) throw new InvalidOperationException();
            source = CreateFile("NUL", 0x40000000, 3, IntPtr.Zero, 3, 0, IntPtr.Zero);
            temporary = true;
        }
        try {
            IntPtr copy;
            if (!DuplicateHandle(GetCurrentProcess(), source, GetCurrentProcess(),
                                 out copy, 0, true, 2)) throw new InvalidOperationException();
            return copy;
        } finally {
            if (temporary) CloseHandle(source);
        }
    }

    public static int Main() {
        StartupInfo startup = new StartupInfo();
        ProcessInfo child = new ProcessInfo();
        try {
            Environment.SetEnvironmentVariable("ANACO_OB_STATE", __STATE__);
            startup.size = Marshal.SizeOf(typeof(StartupInfo));
            startup.flags = 0x100; // STARTF_USESTDHANDLES
            startup.input = InheritableStandardHandle(-10);
            startup.output = InheritableStandardHandle(-11);
            startup.error = InheritableStandardHandle(-12);
            // Inherit binary handles directly: no StreamWriter, encoding or BOM.
            if (!CreateProcess(__PYTHON__, new StringBuilder(__ARGUMENTS__),
                IntPtr.Zero, IntPtr.Zero, true, 0x08000000, IntPtr.Zero, null,
                ref startup, out child)) throw new InvalidOperationException();
            if (WaitForSingleObject(child.process, 0xffffffff) != 0) throw new InvalidOperationException();
            uint code;
            if (!GetExitCodeProcess(child.process, out code)) throw new InvalidOperationException();
            return unchecked((int)code);
        } catch {
            try { Console.Error.WriteLine("Anaco native launcher failed."); } catch { }
            return 1;
        } finally {
            foreach (IntPtr handle in new IntPtr[] {startup.input, startup.output, startup.error, child.thread, child.process}) {
                if (handle != IntPtr.Zero) CloseHandle(handle);
            }
        }
    }
}
'''


def source_for(python, host, state):
    literal = lambda value: '@"' + str(value).replace('"', '""') + '"'
    # Replace placeholders once, so a placeholder inside a path stays literal.
    import re
    values = {'__PYTHON__': python, '__ARGUMENTS__': subprocess.list2cmdline([str(python), str(host)]), '__STATE__': state}
    return re.sub(r'__PYTHON__|__ARGUMENTS__|__STATE__', lambda m: literal(values[m[0]]), SOURCE)


def compile_launcher(source, target):
    """PowerShell compiles once during install, with no access to native IPC."""
    literal = lambda value: "'" + str(value).replace("'", "''") + "'"
    with tempfile.TemporaryDirectory(prefix='.launcher-', dir=target.parent) as temporary:
        folder = Path(temporary)
        code, executable = folder / 'host.cs', folder / 'host.exe'
        code.write_text(source, encoding='utf-8-sig')
        script = ("$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';"
                  f"Add-Type -TypeDefinition ([IO.File]::ReadAllText({literal(code)},[Text.Encoding]::UTF8)) "
                  f"-OutputAssembly {literal(executable)} -OutputType ConsoleApplication")
        encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
        powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        with ManagedProcess([str(powershell), '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            process.communicate(timeout=60)
            if process.returncode or not executable.is_file():
                raise ValueError('No se pudo crear el lanzador nativo de Windows. Comprueba que Windows PowerShell y .NET Framework estén disponibles.')
        os.replace(executable, target)


def launcher(state, python, host):
    source = source_for(python, host, state)
    name = 'native-host-' + hashlib.sha256(source.encode()).hexdigest()[:16] + '.exe'
    target = state / name
    # Versioned names avoid replacing an executable held open by the browser.
    if target.is_symlink():
        raise ValueError('El lanzador nativo no puede ser un enlace simbólico.')
    if not target.is_file():
        compile_launcher(source, target)
    return target

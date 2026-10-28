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
using System.IO;
using System.Diagnostics;
using System.Threading.Tasks;

public static class AnacoNativeHost {
    private static async Task Pump(Stream source, Stream destination, bool closeDestination) {
        try {
            byte[] buffer = new byte[8192];
            int count;
            while ((count = await source.ReadAsync(buffer, 0, buffer.Length)) != 0) {
                await destination.WriteAsync(buffer, 0, count);
                await destination.FlushAsync();
            }
        } finally {
            if (closeDestination) destination.Close();
        }
    }

    public static int Main() {
        try {
            var info = new ProcessStartInfo();
            info.FileName = __PYTHON__;
            info.Arguments = __ARGUMENTS__;
            info.UseShellExecute = false;
            info.CreateNoWindow = true;
            info.RedirectStandardInput = true;
            info.RedirectStandardOutput = true;
            info.RedirectStandardError = true;
            info.EnvironmentVariables["ANACO_OB_STATE"] = __STATE__;
            using (var child = Process.Start(info)) {
                // Background tasks avoid a synchronous pipe read blocking startup.
                Task.Run(() => Pump(Console.OpenStandardInput(), child.StandardInput.BaseStream, true));
                var output = Task.Run(() => Pump(child.StandardOutput.BaseStream, Console.OpenStandardOutput(), false));
                var errors = Task.Run(() => Pump(child.StandardError.BaseStream, Console.OpenStandardError(), false));
                child.WaitForExit();
                Task.WaitAll(output, errors);
                return child.ExitCode;
            }
        } catch {
            Console.Error.WriteLine("Anaco native launcher failed.");
            return 1;
        }
    }
}
'''


def source_for(python, host, state):
    literal = lambda value: '@"' + str(value).replace('"', '""') + '"'
    # Replace placeholders once, so a placeholder inside a path stays literal.
    import re
    values = {'__PYTHON__': python, '__ARGUMENTS__': subprocess.list2cmdline([str(host)]), '__STATE__': state}
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

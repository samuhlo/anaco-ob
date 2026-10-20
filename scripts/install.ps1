# Instala el servicio local de Anaco en Windows · Installs Anaco's local service on Windows.
#   powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/samuhlo/anaco-ob/main/scripts/install.ps1 | iex"
# uv trae su propio Python, así que no hace falta tener Python ni git instalados.
# Sin «exit»: con «irm | iex» cerraría la ventana de PowerShell del usuario.
$ErrorActionPreference = 'Stop'
$Source = if ($env:ANACO_OB_SOURCE) { $env:ANACO_OB_SOURCE } else { 'https://github.com/samuhlo/anaco-ob/archive/refs/heads/main.zip' }

function Step($Text) { Write-Host "`n$Text" -ForegroundColor Yellow }
function Check($What) { if ($LASTEXITCODE -ne 0) { throw "$What ($LASTEXITCODE)" } }

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Step '1/3 · Instalando uv (trae Python) · Installing uv (brings Python)…'
  Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
  $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

Step '2/3 · Instalando Anaco · Installing Anaco…'
uv tool install --force --python 3.12 "anaco-ob @ $Source"; Check 'uv tool install'

Step '3/3 · Registrándolo en Firefox y Zen · Registering it in Firefox and Zen…'
$Bin = (uv tool dir --bin); Check 'uv tool dir'
& (Join-Path $Bin 'anaco-ob.exe') install; Check 'anaco-ob install'

Step 'Listo. Vuelve al navegador: Anaco lo detectará solo · Done. Go back to the browser: Anaco will notice by itself.'

#!/bin/sh
# Instala el servicio local de Anaco en Linux y macOS · Installs Anaco's local service on Linux and macOS.
#   curl -fsSL https://raw.githubusercontent.com/samuhlo/anaco-ob/main/scripts/install.sh | sh
# uv trae su propio Python, así que no hace falta tener Python ni git instalados.
set -eu
SOURCE="${ANACO_OB_SOURCE:-https://github.com/samuhlo/anaco-ob/archive/refs/heads/main.zip}"

step() { printf '\n\033[1m%s\033[0m\n' "$1"; }

if ! command -v uv >/dev/null 2>&1; then
  step "1/3 · Instalando uv (trae Python) · Installing uv (brings Python)…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  PATH="${XDG_BIN_HOME:-$HOME/.local/bin}:$HOME/.cargo/bin:$PATH"
fi

step "2/3 · Instalando Anaco · Installing Anaco…"
uv tool install --force --python 3.12 "anaco-ob @ $SOURCE"

step "3/3 · Registrándolo en Firefox y Zen · Registering it in Firefox and Zen…"
"$(uv tool dir --bin)/anaco-ob" install

step "Listo. Vuelve al navegador: Anaco lo detectará solo · Done. Go back to the browser: Anaco will notice by itself."

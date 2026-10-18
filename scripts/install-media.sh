#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
uv venv .media-venv --allow-existing
uv pip install --python .media-venv/bin/python 'faster-whisper==1.2.1' 'av==16.1.0'
printf '%s\n' 'Motor local instalado. El modelo se descarga al transcribir el primer archivo.'

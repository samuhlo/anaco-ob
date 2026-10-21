#!/usr/bin/env python3
"""Deterministic CLI fixture: a podcast note or a plain video note, as the prompt asks."""
import json
from pathlib import Path
import sys

prompt = sys.stdin.read()
payload = json.loads(prompt[prompt.index('\n\n{') + 2:])
output = Path(sys.argv[sys.argv.index('--output-last-message') + 1])
talk = 'Esta captura es un podcast o una entrevista' in prompt
if payload.get('task') == 'note_connections':
    output.write_text(json.dumps({'existing': [], 'internal': []}))
    sys.exit()
with Path(__file__).with_name('calls.jsonl').open('a') as stream:
    stream.write(json.dumps({'conversation': 'on' if talk else 'off' if 'No uses la forma de conversación' in prompt else 'auto'}) + '\n')
common = {'context': 'Dinero y sentido', 'folder': payload['folders'][0], 'tags': ['economia'], 'relations': [], 'image_captions': [],
          'note_type': 'fuente_externa', 'strategy': 'source', 'rationale': 'Una fuente', 'notes': []}
if talk:
    result = {**common, 'title': 'Conversación sobre dinero', 'source_format': 'podcast', 'author': 'Emilio Duró / Tengo un Plan',
              'body': '## Temas tratados\n\n- [00:04] Dinero y sentido.\n\n%%citas%%\n\n## Qué me llevo\n\n- Revisar si cambio tiempo por dinero.',
              'quotes': [{'text': 'No vendáis vuestra vida por dinero', 'speaker': 'Emilio Duró'}, {'text': 'Una cita que nadie dijo en el programa', 'speaker': ''}]}
else:
    result = {**common, 'title': 'Vídeo sobre dinero', 'source_format': 'video', 'author': '', 'quotes': [], 'body': '## Resumen\n\nUn vídeo sobre dinero.'}
output.write_text(json.dumps(result))

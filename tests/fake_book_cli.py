#!/usr/bin/env python3
"""Deterministic CLI fixture for full-book Native Messaging integration only."""
import json
from pathlib import Path
import sys

prompt = sys.stdin.read()
payload = json.loads(prompt[prompt.index('\n\n{') + 2:])
c = payload['capture']
folder = payload['folders'][0]
output = Path(sys.argv[sys.argv.index('--output-last-message') + 1])
model = sys.argv[sys.argv.index('--model') + 1]
log = Path(__file__).with_name('calls.jsonl')
with log.open('a') as stream:
    stream.write(json.dumps({'scope': c.get('reader', {}).get('scope'),
                             'pages': c.get('reader', {}).get('pages'),
                             'image_count': sys.argv.count('--image')}) + '\n')
result = {'title': 'Complete cloud book', 'context': 'Lectura de todas las páginas',
          'body': '## // RESUMEN\n\n' + c['text'], 'folder': folder, 'tags': ['cloud'],
          'relations': [], 'image_captions': [{'index': i, 'description': 'Diagram of identity, policy and resource.', 'useful': True} for i in c.get('vision_images', [])]}
output.write_text(json.dumps(result))

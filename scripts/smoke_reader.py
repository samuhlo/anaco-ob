#!/usr/bin/env python3
"""Read a small synthetic book with the real CLI; leaves the personal vault alone."""
import argparse
import base64
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'native'))
from core import App
from reader import Reader

parser = argparse.ArgumentParser()
parser.add_argument('--source-state', type=Path, required=True)
parser.add_argument('--ai', action='store_true')
args = parser.parse_args()
if not args.ai:
    parser.error('This smoke consumes two model requests with synthetic content; pass --ai explicitly.')
source = next(args.source_state.glob('readers/*/book.json')).parent
out = ROOT / '.test-artifacts/reader-ai'
out.mkdir(parents=True, exist_ok=True)
run = Path(tempfile.mkdtemp(prefix='run-', dir=out))
vault = run / 'Vault'
(vault / '02_Cerebro/Cloud').mkdir(parents=True)
(vault / '99_Recursos').mkdir()
app = App(run / 'state')
app.set_config({'vault': str(vault), 'provider': 'codex'})
app.progress = lambda message: print(message, flush=True)
reader = Reader(app)
job = reader.begin({'url': 'https://example.org/synthetic-book', 'title': 'Libro de prueba: identidad, política y recursos', 'count': 3, 'identity': 'synthetic-three-pages'})['job']
for index in range(1, 4):
    page = json.loads((source / f'page-{index}.json').read_text())
    raw = (source / page['file']).read_bytes()
    reader.page_begin({'job': job, 'index': index, 'size': len(raw), 'text': page['text']})
    for offset in range(0, len(raw), 393216):
        reader.chunk({'job': job, 'index': index, 'offset': offset, 'data': base64.b64encode(raw[offset:offset + 393216]).decode()})
    reader.page_finish({'job': job, 'index': index})
capture = reader.finish({'job': job})
result = app.draft(capture['id'], provider='codex')
stored = app.load(capture['id'])
assert stored['reader']['analyzed_pages'] == 3
assert len([p for p in reader.directory(job).glob('analysis-*.json')]) == 1
assert len(result['draft']['body']) > 100
assert all(i.get('caption') for i in stored['images'])
report = {'passed': True, 'real_models': stored['media']['reading_models'], 'pages_read': 3,
          'batch_then_synthesis': True, 'captions': [i['caption'] for i in stored['images']],
          'summary': result['draft']['body'], 'state': str(run / 'state')}
(out / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False, indent=2))
app.db.close()

#!/usr/bin/env python3
"""Synthetic PDF + real local ASR + optional real visual summary, outside the personal vault."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'native'),str(ROOT/'tests')]
from core import App
from media import Media
from media_fixtures import make_pdf
from fixture_vault import classic_profile

parser=argparse.ArgumentParser();parser.add_argument('--vision',action='store_true');parser.add_argument('--audio',type=Path)
args=parser.parse_args()
out=ROOT/'.test-artifacts/media';out.mkdir(parents=True,exist_ok=True)
run_dir=Path(tempfile.mkdtemp(prefix='run-',dir=out));vault=run_dir/'Vault';(vault/'02_Cerebro/Tech_&_Codigo').mkdir(parents=True)
app=App(run_dir/'state');app.set_config({'vault':str(vault),'provider':'codex' if args.vision else 'manual'});classic_profile(app)
pdf=make_pdf(run_dir/'fixtures');capture=Media(app).pdf(pdf,'AWS: identidad y permisos','https://example.org/aws.pdf')
assert 'Least privilege' in capture['text'] and len(capture['images'])==2
result=app.draft(capture['id'],'Quiero estudiar IAM y entender el diagrama de permisos.',provider='codex' if args.vision else 'manual')
if args.vision:
    captions=[i.get('caption','') for i in result['capture']['images']]
    assert all(len(c)>40 for c in captions),captions
    assert any('pol' in c.lower() and ('ident' in c.lower() or 's3' in c.lower()) for c in captions),captions
    assert result['draft']['model']=='gpt-6.1-sol'
saved=app.save(capture['id'],{})
note=Path(saved['path']).read_text();assert 'descripción pendiente' not in note
report={'pdf_text':True,'pdf_pages':2,'visual_summary':args.vision,'model':result['draft']['model'],'note':saved['path'],'captions':[i.get('caption') for i in result['capture']['images']]}
if args.audio:
    audio=Media(app).audio(args.audio.resolve(),'Audio de prueba','https://example.org/audio')
    assert len(audio['text'])>60 and '[00:' in audio['text'],audio['text']
    report['local_transcription']={'passed':True,'language':audio['media'].get('language'),'method':audio['media']['method'],'characters':len(audio['text'])}
(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))

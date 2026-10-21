#!/usr/bin/env python3
"""Real podcast from YouTube with Codex, saved into a copy of the vault; the real vault is only read."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'native'))
from core import App
from media import Media
from vault_profile import install

URL='https://www.youtube.com/watch?v=79Ypa2k36gk'
INTENT='Quiero entender cómo proteger mis ahorros ante una crisis y qué aplicar yo con mi sueldo.'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default=URL);parser.add_argument('--intent',default=INTENT)
    parser.add_argument('--vault',type=Path,help='Vault whose notes, resources and profile are copied (default: the configured one)');args=parser.parse_args()
    real=App();source=args.vault or real.vault();settings=real.config();real.db.close()
    out=ROOT/'.test-artifacts/podcast';out.mkdir(parents=True,exist_ok=True)
    run=Path(tempfile.mkdtemp(prefix='run-',dir=out));vault=run/'Vault'
    for folder in ('02_Cerebro','99_Recursos'):
        shutil.copytree(source/folder,vault/folder,ignore=shutil.ignore_patterns('adjuntos','.*'))
    for folder in ('03_Proyectos','04_Cajon_Ideas','07_Clases'):(vault/folder).mkdir(parents=True,exist_ok=True)
    if (source/'AGENTS.md').is_file():shutil.copyfile(source/'AGENTS.md',vault/'AGENTS.md')
    app=App(run/'state')
    app.set_config({'vault':str(vault),'provider':'codex','model':settings['model'],'vision_model':settings['vision_model'],'note_structure':settings['note_structure']})
    config=json.loads((run/'state/config.json').read_text());config['codex']=settings['codex'];(run/'state/config.json').write_text(json.dumps(config))
    install(app,json.loads((vault/settings['profile_path']).read_text()),settings['profile_path'])
    app.progress=lambda value:print('  ·',value if isinstance(value,str) else value.get('message',value),flush=True)
    started=time.monotonic()
    try:
        c=Media(app).video_url({'url':args.url});stored=app.load(c['id'])
        print(f"Transcripción: {len(stored['text'])} caracteres, {len(stored['media'].get('chapters',[]))} capítulos, canal {stored['author']!r}",flush=True)
        result=app.draft(c['id'],args.intent,provider='codex');draft=result['draft']
        links=app.handle({'action':'refresh_links','id':c['id'],'fields':{}})
        relations=[r['path'] for r in links['notes'].get('source',{}).get('relations',[])]
        markdown=app.preview(c['id'],{'relations':relations})['markdown']
        saved=app.save(c['id'],{'relations':relations})
        note=Path(saved['path']).read_text()
        quotes=re.findall(r'^> «.+» .*· \[[\d:]+\]\(https://www\.youtube\.com/watch\?v=[\w-]{11}&t=\d+s\)$',note,re.M)
        anchored=re.findall(r'^- \[\[[^\]|#]+#[^\]|]+\]\]',note,re.M)
        report={'url':args.url,'seconds':round(time.monotonic()-started),'duration_seconds':stored['media'].get('duration_seconds'),'transcript_characters':len(stored['text']),
                'chapters':len(stored['media'].get('chapters',[])),'coverage':app.load(c['id'])['media'].get('coverage'),'source_format':draft['source_format'],
                'author':draft.get('author') or stored['author'],'rationale':draft.get('rationale'),'quotes':len(quotes),
                'time_links':len(re.findall(r'&t=\d+s\)',note)),'relations':len(relations),'section_links':len(anchored),'connection_model':links['stats'].get('model'),
                'note':saved['relative'],'path':saved['path'],'preview_matches_saved':markdown.split('\n---\n',1)[1]==note.split('\n---\n',1)[1]}
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
        assert report['source_format'] in ('podcast','entrevista') and report['quotes'] and report['time_links'],report
    finally:app.db.close()


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Test a real split plan for the Codrops note, entirely in a fixture vault."""
import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'native'))
from core import App
from editorial import Editorial
from splitting import blocks


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ai',action='store_true');args=parser.parse_args()
    if not args.ai:parser.error('--ai permite una solicitud con la nota del artículo público y una anotación ficticia.')
    source=json.loads((ROOT/'.test-artifacts/code-notes-eval/single/proposal.json').read_text())
    out=ROOT/'.test-artifacts/split-review-ai';out.mkdir(exist_ok=True,parents=True)
    run=Path(tempfile.mkdtemp(prefix='run-',dir=out));vault=run/'Vault'
    for folder in ('02_Cerebro/Tech_&_Codigo','02_Cerebro/Modelos_Mentales','99_Recursos'):(vault/folder).mkdir(parents=True,exist_ok=True)
    app=App(run/'state')
    try:
        app.set_config({'vault':str(vault),'provider':'codex'})
        c=app.stage({'kind':'article','url':source['url'],'title':source['title'],'text':source['text']})
        c=app.load(c['id']);c['draft']=copy.deepcopy(source['draft']);c['status']='draft';app.store(c)
        body=c['draft']['body']+'\n\n## Comentario personal\nMI ANOTACIÓN: probar una letra antes de ampliar la composición.\n'
        fields={'notes':{'source':{'body':body,'images':[],'captions':{}}},'selected_notes':['source'],'active_note':'source','merged_into':{}}
        before=app.load(c['id'])
        proposal=app.handle({'action':'propose_split','id':c['id'],'note':'source','fields':fields})
        (out/'suggestion.json').write_text(json.dumps(proposal,ensure_ascii=False,indent=2))
        assert proposal['recommended'] and len(proposal['notes'])>=2
        assert app.load(c['id'])==before,'Cambió la nota sin aceptar'
        assert not list(vault.rglob('*.md'))
        for part in blocks(body):assert sum(part['body'] in n['body'] for n in proposal['notes'])==1,'Se perdió o duplicó un bloque'
        applied=app.handle({'action':'split_decision','id':c['id'],'proposal':proposal['id'],'decision':'accept','fields':fields})
        assert not list(vault.rglob('*.md')),'Se guardó antes de revisar'
        stored=app.load(c['id'])
        for key,note in Editorial(app).drafts(stored).items():
            markdown=app.preview(c['id'],{**applied['fields'],'active_note':key})['markdown']
            (out/(key+'.md')).write_text(markdown)
        saved=app.save(c['id'],applied['fields'])
        report={'passed':True,'model':stored['draft']['model'],'suggested_topics':len(proposal['notes']),'saved_notes':saved['count'],'no_change_before_accept':True,'all_edited_blocks_preserved_exactly_once':True,'no_vault_writes_before_save':True,'original_code_and_personal_annotation_preserved':True,'rationale':proposal['rationale'],'fixture_vault':str(vault)}
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
    finally:app.db.close()


if __name__=='__main__':main()

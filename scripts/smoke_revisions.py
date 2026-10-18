#!/usr/bin/env python3
"""Real scoped revision and merge, in an isolated synthetic vault."""
import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'native'))
from core import App
from fixture_vault import classic_profile

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ai',action='store_true');args=parser.parse_args()
    if not args.ai:parser.error('--ai utiliza el modelo con datos ficticios.')
    out=ROOT/'.test-artifacts/revisions-ai';out.mkdir(parents=True,exist_ok=True);run=Path(tempfile.mkdtemp(prefix='run-',dir=out));vault=run/'Vault';folder='02_Cerebro/Tech_&_Codigo';(vault/folder).mkdir(parents=True)
    app=App(run/'state');app.set_config({'vault':str(vault)});classic_profile(app)
    source='Una identidad solicita acceso a un recurso. La política establece las acciones permitidas sobre ese recurso. El mínimo privilegio limita esas acciones a lo necesario. Un rol puede proporcionar permisos temporales a un servicio. La fuente no ofrece una configuración concreta.'
    c=app.stage({'url':'https://example.org/permissions','title':'Permisos y roles','text':source});app.draft(c['id'],provider='manual');c=app.load(c['id']);c['draft'].update(folder=folder,body='## Permisos\nLa política decide acciones permitidas.\n\n## Comentario personal\nMI COMENTARIO: revisar este punto con el profesor.')
    other=copy.deepcopy(c['draft']);other.update(id='roles',title='Roles temporales',filename='nota_roles_temporales.md',note_type='referencia_tecnica',body='## Roles\nUn rol puede proporcionar permisos temporales a un servicio.',links=[],source_pages=[],source_evidence=source,selected_images=[])
    c['bundle']={'notes':[other],'rationale':'Dos aspectos relacionados de la fuente.'};app.store(c)
    fields={'notes':{},'selected_notes':['source','roles'],'active_note':'source'}
    revised=app.handle({'action':'revise','id':c['id'],'note':'source','fields':fields,'section':'0','mode':'clarify','instruction':'Explica qué decide la política y en qué recurso se aplica.'})
    assert revised['after'].endswith('## Comentario personal\nMI COMENTARIO: revisar este punto con el profesor.')
    fields['notes']['source']={'body':revised['after'],'revision_model':revised['model']}
    merged=app.handle({'action':'revise','id':c['id'],'note':'source','fields':fields,'section':'all','mode':'merge','other':'roles'})
    assert 'MI COMENTARIO: revisar este punto con el profesor.' in merged['after']
    fields.update(selected_notes=['source'],merged_into={'roles':'source'});fields['notes']['source'].update(body=merged['after'],revision_model=merged['model'])
    preview=app.preview(c['id'],fields);assert 'llm_asistido: true' in preview['markdown'];assert 'nota_roles_temporales' not in preview['markdown']
    (out/'revised.md').write_text(revised['after']);(out/'merged.md').write_text(preview['markdown']);app.save(c['id'],fields)
    report={'passed':True,'model':merged['model'],'scoped_revision_preserves_comment':True,'merge_preserves_comment':True,'merged_selection':1,'saved':True,'state':str(run/'state')};(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2));app.db.close()
if __name__=='__main__':main()

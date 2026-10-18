#!/usr/bin/env python3
"""Exercise structure choices and code selection with the configured text model.

Requires the real Codrops capture produced by tests/e2e_zen.py --code.
All drafts and notes stay in isolated fixture vaults.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'native'))
from core import App
from editorial import Editorial


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ai',action='store_true');args=parser.parse_args()
    if not args.ai:parser.error('--ai permite solicitudes con el artículo público y una fuente ficticia.')
    captured=json.loads((ROOT/'.test-artifacts/zen-code/captured.json').read_text())
    source=json.loads((ROOT/'.test-artifacts/codrops-code/source.json').read_text())
    out=ROOT/'.test-artifacts/code-notes-eval';out.mkdir(exist_ok=True,parents=True)
    fence=re.compile(r'^(`{3,}|~{3,})[^\n]*\n(.*?)^\1[ \t]*$',re.M|re.S)

    def run(case):
        name,mode,text=case;directory=out/name;directory.mkdir(exist_ok=True)
        vault=directory/'Vault'
        for path in ('02_Cerebro/Tech_&_Codigo','02_Cerebro/Modelos_Mentales','99_Recursos'):(vault/path).mkdir(parents=True,exist_ok=True)
        app=App(directory/'state')
        try:
            app.set_config({'vault':str(vault),'provider':'codex','note_structure':mode})
            c=app.stage({'kind':'article','url':'https://tympanus.net/codrops/2026/10/13/scroll-driven-ghost-trails/' if name!='no-code' else 'https://example.org/design','title':captured['title'] if name!='no-code' else 'Decisiones editoriales','text':text})
            app.draft(c['id'],intent='Entender las técnicas y poder consultar después los ejemplos que aporten valor.',provider='codex')
            c=app.load(c['id']);(directory/'proposal.json').write_text(json.dumps(c,ensure_ascii=False,indent=2))
            notes=Editorial(app).drafts(c);blocks=[]
            for key,note in notes.items():
                markdown=app.preview(c['id'],{'notes':{},'active_note':key})['markdown']
                (directory/(key+'.md')).write_text(markdown)
                blocks.extend(m.group(2).strip() for m in fence.finditer(note['body']))
            if name=='no-code':assert not blocks,'Se inventó código sin fuente'
            else:
                assert 0<len(blocks)<len(source['code']),'No seleccionó una muestra útil de código'
                assert all(any(block in original for original in source['code']) for block in blocks),'Modificó o inventó código'
                if mode=='single':assert len(notes)==1,'Ignoró una sola nota'
                if mode=='linked':assert len(notes)>1,'No dividió las técnicas solicitadas'
            result={'case':name,'mode':mode,'notes':len(notes),'selected_code_blocks':len(blocks),'literal_code':True,'model':c['draft']['model']}
            print(json.dumps(result),flush=True);return result
        finally:app.db.close()

    cases=[('single','single',captured['text']),('linked','linked',captured['text']),('no-code','single','El rediseño da más espacio a los títulos y reduce los elementos del encabezado para facilitar el recorrido de lectura. El caso presenta decisiones visuales, no código ni ejemplos de implementación. No aporta métricas de conversión ni permite atribuir un resultado causal al rediseño.')]
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,cases))
    report={'passed':True,'quality':'Checks of structure and literal code; teaching quality requires user review','source_blocks':len(source['code']),'results':results}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()

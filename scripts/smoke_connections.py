#!/usr/bin/env python3
"""Check semantic connections without changing captures or vault notes."""
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
from linking import calculate
from fixture_vault import classic_profile


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ai',action='store_true');parser.add_argument('--real-vault',action='store_true');args=parser.parse_args()
    if not args.ai:parser.error('--ai permite una solicitud de conexiones. --real-vault usa en modo lectura la propuesta Codrops y candidatas del usuario.')
    out=ROOT/'.test-artifacts'/('real-connections' if args.real_vault else 'connections-ai');out.mkdir(exist_ok=True,parents=True)
    if args.real_vault:
        app=App();captures=[]
        for path in (app.state/'captures').glob('*.json'):
            c=json.loads(path.read_text())
            if c.get('vault')==str(app.vault()) and c.get('status')=='draft' and 'scroll-driven-ghost' in c.get('url',''):captures.append((path.stat().st_mtime,c))
        c=max(captures,key=lambda v:v[0])[1]
    else:
        run=Path(tempfile.mkdtemp(prefix='run-',dir=out));vault=run/'Vault'
        for folder in ('02_Cerebro/Tech_&_Codigo','02_Cerebro/Modelos_Mentales','99_Recursos'):(vault/folder).mkdir(parents=True,exist_ok=True)
        (vault/'02_Cerebro/Tech_&_Codigo/nota_gsap_ticker.md').write_text('# GSAP: ticker y limpieza\n\nEl ticker de GSAP registra callbacks que actualizan el renderizado en cada cuadro. Cuando se desmonta un componente se debe retirar su callback con gsap.ticker.remove para evitar duplicar ciclos de dibujo. Los tweens cambian valores de estado que el renderizador puede leer, en vez de animar necesariamente nodos DOM.')
        (vault/'02_Cerebro/Tech_&_Codigo/nota_estado_y_render.md').write_text('# Separar estado y dibujo\n\nUn bucle de animación puede actualizar el estado y dejar que cada renderizador interprete esos valores. Un progreso entre cero y uno puede controlar tanto una transición dibujada en Canvas como un uniforme que determina la revelación de una imagen en un shader.')
        (vault/'02_Cerebro/Tech_&_Codigo/nota_gsap_noticias.md').write_text('# Noticias de GSAP\n\nEsta nota únicamente registra que se mencionó la marca en una reunión. No contiene técnicas, mecanismos de animación ni documentación de implementación.')
        app=App(run/'state');app.set_config({'vault':str(vault),'provider':'codex'});classic_profile(app)
        source=json.loads((ROOT/'.test-artifacts/code-notes-eval/linked/proposal.json').read_text())
        c=app.stage({'kind':'article','title':source['title'],'url':source['url'],'text':source['text']});c=app.load(c['id'])
        c.update(draft=copy.deepcopy(source['draft']),bundle=copy.deepcopy(source['bundle']),status='draft');app.store(c)
    try:
        before=app.load(c['id'])
        result=calculate(app,c,{'notes':{},'selected_notes':list(Editorial(app).drafts(c)),'active_note':'source'})
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
        external=[(key,r) for key,values in result['external'].items() for r in values]
        gsap=[r['path'] for _,r in external if 'gsap' in r['path'].lower()]
        assert gsap and result['stats']['internal']>0,'Faltan conexiones GSAP o relaciones entre temas'
        assert app.load(c['id'])==before,'La comprobación modificó el borrador'
        if not args.real_vault:assert all('noticias' not in r['path'] for _,r in external),'Relacionó una mención sin mecanismo útil'
        report={'passed':True,'read_only':True,'real_vault':args.real_vault,'model':result['stats']['model'],'external':result['stats']['external'],'sibling_pairs':result['stats']['internal'],'gsap_suggestions':len(gsap),'capture_unchanged':True,'paths':sorted(set(gsap))}
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
    finally:app.db.close()


if __name__=='__main__':main()

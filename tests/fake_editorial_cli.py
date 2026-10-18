#!/usr/bin/env python3
"""Deterministic editorial proposal for browser integration, no model requests."""
import json
from pathlib import Path
import sys
import time

prompt=sys.stdin.read();payload=json.loads(prompt[prompt.index('\n\n{')+2:])
delay=Path(__file__).with_name('delay-once')
if delay.exists():delay.unlink();Path(__file__).with_name('delay-started').write_text('started');time.sleep(30)
if payload.get('task')=='note_connections':
    existing=[];internal=[];notes=[n for n in payload['notes'] if n['evidence']];candidates=[n for n in payload['candidates'] if n['evidence']]
    if candidates:
        for note in notes:
            existing.append({'from':note['id'],'to':candidates[0]['id'],'from_evidence':note['evidence'][0]['id'],'to_evidence':candidates[0]['evidence'][0]['id'],'kind':'aplica','reason':'Aplica el mecanismo de estudio descrito en la nota existente.'})
    themes=[n for n in notes if n['id']!='source']
    if len(themes)>1:internal=[{'from':themes[0]['id'],'to':themes[1]['id'],'from_evidence':themes[0]['evidence'][0]['id'],'to_evidence':themes[1]['evidence'][0]['id'],'kind':'requisito','reason':'Comprender la explicación permite aplicar y revisar después el procedimiento.'}]
    Path(sys.argv[sys.argv.index('--output-last-message')+1]).write_text(json.dumps({'existing':existing,'internal':internal}));raise SystemExit()
if payload.get('task')=='split_note':
    ids=[v['id'] for v in payload['blocks']];middle=max(1,len(ids)//2)
    result={'recommended':True,'rationale':'Hay dos temas útiles para consultar por separado sin perder los ejemplos ni tus anotaciones.','summary':'Síntesis de la explicación y la práctica de estudio.',
            'groups':[{'title':'Comprender y explicar','purpose':'Consultar las ideas y su explicación.','note_type':'nota_atomica','block_ids':ids[:middle],'images':[]},
                      {'title':'Aplicar y revisar','purpose':'Conservar el procedimiento y los comentarios de consulta.','note_type':'referencia_tecnica','block_ids':ids[middle:],'images':[]}]}
    Path(sys.argv[sys.argv.index('--output-last-message')+1]).write_text(json.dumps(result));raise SystemExit()
if 'fragment' in payload:
    result={'body':payload['fragment'].strip()+'\n\nExplicación ajustada conservando la información de la fuente.'}
    if payload.get('other_note'):result['body']+='\n\n'+payload['other_note']
    Path(sys.argv[sys.argv.index('--output-last-message')+1]).write_text(json.dumps(result));raise SystemExit()
c=payload['capture']
folder=next(p for p in payload['folders'] if p.endswith('Tech_&_Codigo'))
common={'folder':folder,'tags':['estudio'],'relations':[],'images':[],'pages':[],
        'source_evidence':c['text'][:100],'context':'Apartado fundamentado en la fuente','links':[]}
result={'title':'Mapa de estudio','context':'Síntesis y conexiones de los apartados','body':'## Síntesis\n\nEl estudio combina comprensión, recuperación y revisión.',
        'folder':folder,'tags':['estudio'],'relations':[],'image_captions':[],
        'note_type':'indice','strategy':'collection','source_format':'articulo','rationale':'Tres temas que conviene estudiar por separado y conectar.',
        'notes':[{**common,'id':'comprension','title':'Comprender lo estudiado','note_type':'nota_atomica','body':'## Comprensión\n\nExplicar con tus palabras ayuda a detectar lagunas.',
                  'links':[{'id':'recuperacion','reason':'Recuperar lo comprendido permite comprobar el aprendizaje.'}]},
                 {**common,'id':'recuperacion','title':'Recuperar sin mirar','note_type':'referencia_tecnica','body':'## Práctica\n\nIntenta recordar antes de consultar los apuntes.'},
                 {**common,'id':'revision','title':'Revisar los errores','note_type':'nota_atomica','body':'## Revisión\n\nLos errores orientan la siguiente sesión.'}]}
for i in c.get('vision_images',[]):result['image_captions'].append({'index':i,'description':'Diagrama del ciclo de estudio y recuperación.','useful':True})
Path(sys.argv[sys.argv.index('--output-last-message')+1]).write_text(json.dumps(result))

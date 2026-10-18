#!/usr/bin/env python3
"""Real editorial behavior on synthetic sources, never on the personal vault."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'native'))
from core import App
from reader import Reader

parser=argparse.ArgumentParser();parser.add_argument('--ai',action='store_true');parser.add_argument('--resume-run',type=Path);args=parser.parse_args()
if not args.ai:parser.error('Pass --ai to consume model requests with the synthetic cases.')
out=ROOT/'.test-artifacts/editorial-ai';out.mkdir(parents=True,exist_ok=True)
run=args.resume_run.resolve() if args.resume_run else Path(tempfile.mkdtemp(prefix='run-',dir=out));vault=run/'Vault'
for rel in ('02_Cerebro/Modelos_Mentales','02_Cerebro/Tech_&_Codigo','07_Clases/01_AWS/01_Fundamentos','99_Recursos'):(vault/rel).mkdir(parents=True,exist_ok=True)
app=App(run/'state');app.set_config({'vault':str(vault),'provider':'codex'});app.progress=lambda message:print(message,flush=True)
reader=Reader(app)
generate=app.codex_generate
def record(c,*args,**kwargs):
    result=generate(c,*args,**kwargs)
    label=c.get('reader',{}).get('scope') or c['id']
    (run/('proposal-'+str(label).replace('/','-')+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
    return result
app.codex_generate=record
texts=[
 'Identidades y permisos. Un usuario identifica a una persona y un rol proporciona permisos temporales que puede asumir un servicio. Una política define acciones y recursos permitidos. El principio de mínimo privilegio concede únicamente los permisos necesarios. El caso de un servicio que lee un bucket ilustra la relación entre rol, política y recurso.',
 'Cómputo con instancias. Una instancia EC2 es una máquina virtual cuya capacidad se elige según la carga. Una imagen contiene el sistema y configuración inicial. Los grupos de seguridad controlan el tráfico permitido. Detener una instancia y terminarla tienen efectos distintos sobre su ciclo de vida. El caso propuesto consiste en elegir capacidad para una aplicación web y justificar sus accesos de red.',
 'Almacenamiento de objetos. S3 organiza objetos dentro de buckets; cada objeto tiene una clave. Una política de acceso determina quién puede leer o escribir. El versionado conserva versiones y facilita recuperar cambios accidentales. Un ciclo de vida puede mover o eliminar objetos siguiendo reglas temporales. El ejemplo compara almacenar archivos de una web con ejecutar la aplicación en una instancia.'
]
if args.resume_run:
    meta=json.loads(next((run/'state/readers').glob('*/book.json')).read_text());c=app.load(meta['capture'])
else:
    job=reader.begin({'count':3,'url':'https://example.org/synthetic-cloud-book','title':'Fundamentos de cloud: identidades, cómputo y almacenamiento','identity':'editorial-fixture'})['job']
    for index,text in enumerate(texts,1):reader.page_begin({'job':job,'index':index,'size':0,'text':text});reader.page_finish({'job':job,'index':index})
    c=reader.finish({'job':job})
book=app.draft(c['id'],intent='Preparar apuntes por apartados para estudiar este módulo de AWS, con una síntesis que los conecte.',provider='codex')
stored=app.load(c['id'])
assert len(stored.get('bundle',{}).get('notes',[]))>=2,'The three-topic course must propose related notes.'
assert stored['draft']['strategy']=='collection'
book_files=app.save(c['id'],{})
for path in book_files['paths']:
    content=(vault/path).read_text()
    assert '[[' in content
    (out/('book-'+Path(path).name)).write_text(content)
print('Curso:',book_files['count'],'notas; tipo principal:',stored['draft']['note_type'],flush=True)
c=app.stage({'kind':'article','url':'https://tympanus.net/codrops/synthetic-design-case','title':'Caso ficticio: rediseño de una web editorial',
 'text':'El equipo rediseñó una web editorial para mejorar la jerarquía de lectura. Redujo el ruido visual del encabezado, dio mayor espacio a los títulos y reservó la animación para transiciones que ayudan a comprender el recorrido. El resultado del caso se explica como una decisión de diseño particular; no se aportan métricas de conversión ni un experimento que pruebe causalidad.'})
article=app.draft(c['id'],intent='Guardar este caso de diseño como referencia y sus aprendizajes aplicables.',provider='codex');article_stored=app.load(c['id'])
assert article_stored['draft']['note_type']=='fuente_externa'
assert not article_stored.get('bundle'),'The short design case should remain one source note.'
(out/'design-case.md').write_text(app.preview(c['id'],{})['markdown'])
print('Caso de diseño:',article_stored['draft']['note_type'],flush=True)
c=app.stage({'kind':'article','url':'https://example.org/synthetic-inversion','title':'La inversión como forma de pensar',
 'text':'La inversión propone examinar un objetivo preguntando primero qué acciones asegurarían su fracaso. Identificar esas condiciones permite detectar errores evitables y diseñar restricciones. No sustituye la búsqueda directa de soluciones: complementa el razonamiento al hacer visibles riesgos que se pasan por alto. Un ejemplo consiste en preguntar qué haría imposible mantener un hábito y reducir esas condiciones. El método tiene límites cuando la lista de riesgos impide actuar o cuando se confunde evitar el fracaso con garantizar el éxito.'})
mental=app.draft(c['id'],intent='Destilar el mecanismo como modelo mental reutilizable para la sección Modelos Mentales, con sus límites.',provider='codex');mental_stored=app.load(c['id'])
assert mental_stored['draft']['note_type']=='modelo_mental'
assert mental_stored['draft']['folder']=='02_Cerebro/Modelos_Mentales'
(out/'mental-model.md').write_text(app.preview(c['id'],{})['markdown'])
print('Concepto:',mental_stored['draft']['note_type'],flush=True)
report={'passed':True,'model':book['draft']['model'],'book_note_count':book_files['count'],'book_primary_type':stored['draft']['note_type'],
 'book_notes':[{'title':n['title'],'type':n['note_type'],'folder':n['folder']} for n in stored['bundle']['notes']],
 'design_type':article_stored['draft']['note_type'],'design_single_note':not bool(article_stored.get('bundle')),
 'mental_type':mental_stored['draft']['note_type'],'mental_folder':mental_stored['draft']['folder'],'state':str(run/'state')}
(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2));app.db.close()

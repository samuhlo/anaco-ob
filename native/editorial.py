"""Editorial decisions, typed notes and reviewable linked note collections."""
import copy
import datetime as dt
import json
import hashlib
import re
from urllib.parse import quote
from core import UserError, clean, safe_path, slug, write_new_atomic

TYPES = {
    'fuente_externa':'Fuente externa', 'nota_atomica':'Nota de conocimiento',
    'modelo_mental':'Modelo mental', 'referencia_tecnica':'Referencia técnica',
    'indice':'Índice', 'apunte':'Apunte', 'resumen':'Resumen', 'ejercicio':'Ejercicio',
    'practica':'Práctica', 'examen':'Examen', 'otro':'Otro material de clase',
    'idea':'Idea', 'proyecto':'Proyecto'
}
CLASS_TYPES = ('apunte','resumen','ejercicio','practica','examen','otro','indice')
RELATION_KINDS=('relaciona','explica','aplica','contrasta','amplia','requisito','ejemplo')


def allowed_types(folder):
    if folder.startswith('07_Clases/'):
        return list(CLASS_TYPES)
    if folder.startswith('02_Cerebro/'):
        values=['fuente_externa','nota_atomica','referencia_tecnica','indice']
        if folder.endswith('/Modelos_Mentales'):
            values.insert(2,'modelo_mental')
        return values
    return ['fuente_externa','nota_atomica','referencia_tecnica','indice','idea','proyecto']


def note_type(folder, value=None):
    value=value or ('resumen' if folder.startswith('07_Clases/') else 'fuente_externa')
    if value not in allowed_types(folder):
        raise UserError('El tipo de nota no encaja con el destino. Revisa el tipo y la carpeta.')
    return value


def filename(capture, title, folder, kind=None):
    kind=note_type(folder,kind)
    if folder.startswith('07_Clases/'):
        return f"{kind}_{capture['created'][:10]}_{slug(title,'-')}.md"
    if kind=='fuente_externa':
        suffix=('_frase_' if capture['kind']=='quote' else '_imagen_' if capture['kind']=='image' else '')
        if suffix:suffix+=capture.get('source_fingerprint',capture['fingerprint'])[:6]
        return f"fuente_{capture['created'][:10]}_{slug(title)}{suffix}.md"
    if kind=='indice':
        return f'nota_indice_{slug(title)}.md'
    return f'nota_{slug(title)}.md'


def validate_filename(name, kind, folder):
    if folder.startswith('07_Clases/'):
        pattern=rf'{kind}_\d{{4}}-\d{{2}}-\d{{2}}_[a-z0-9-]+\.md'
    elif kind=='fuente_externa':
        pattern=r'fuente_\d{4}-\d{2}-\d{2}_[a-z0-9_]+\.md'
    else:
        pattern=r'nota_[a-z0-9_]+\.md'
    if not re.fullmatch(pattern,name):
        raise UserError('El nombre del archivo no corresponde al tipo de nota y destino elegidos.')


def extend_schema(properties, relation):
    types={'type':'string','enum':list(TYPES)}
    links={'type':'array','items':{'type':'object','properties':{'id':{'type':'string'},'reason':{'type':'string'},'kind':{'type':'string','enum':list(RELATION_KINDS)}},'required':['id','reason','kind'],'additionalProperties':False}}
    child={k:{'type':'string'} for k in ('id','title','context','body','folder','source_evidence')}
    child['id']={'type':'string','pattern':'^tema-[a-z0-9-]{1,50}$'}
    child.update(note_type=types,tags={'type':'array','items':{'type':'string'}},
                 pages={'type':'array','items':{'type':'integer'}},
                 images={'type':'array','items':{'type':'integer'}},links=links,
                 relations={'type':'array','items':relation})
    properties.update(note_type=types,strategy={'type':'string','enum':['source','study','concept','reference','collection','quote','image','reading']},
                      rationale={'type':'string'},source_format={'type':'string','enum':['articulo','libro','documento','video','podcast','hilo']},
                      notes={'type':'array','items':{'type':'object','properties':child,'required':list(child),'additionalProperties':False}})


def guidance(capture):
    from prompts import guidance as build
    return build(capture)


def format_pages(pages):
    values=sorted(set(pages));groups=[]
    for n in values:
        if groups and n==groups[-1][-1]+1:groups[-1].append(n)
        else:groups.append([n])
    return ', '.join(str(v[0]) if len(v)==1 else f'{v[0]}–{v[-1]}' for v in groups)


class Editorial:
    def __init__(self,app): self.app=app

    def validate_relations(self,c,values,candidates):
        found=[];known={v['path']:v for v in candidates}
        for value in values[:8] if isinstance(values,list) else []:
            if not isinstance(value,dict) or value.get('path') not in known:continue
            a,b=clean(value.get('source_evidence'),800).strip(),clean(value.get('note_evidence'),800).strip()
            if len(a)<15 or len(b)<15 or a not in c['text'] or b not in known[value['path']]['excerpt']:continue
            found.append({'path':value['path'],'reason':clean(value.get('reason'),1000),'kind':value.get('kind') if value.get('kind') in RELATION_KINDS else 'relaciona','source_evidence':a,'note_evidence':b,'accepted':False})
        return found

    def build(self,c,result,root,candidates,folders):
        root['note_type']=note_type(root['folder'],result.get('note_type'))
        root['filename']=filename(c,root['title'],root['folder'],root['note_type'])
        root['strategy']=result.get('strategy') or ('study' if c.get('reader') or c['kind'] in ('pdf','video') else 'source')
        root['rationale']=clean(result.get('rationale'),1600)
        root['source_format']=result.get('source_format') or ('libro' if c.get('reader') else 'video' if c['kind']=='video' else 'documento' if c['kind'] in ('pdf','image') else 'articulo')
        children=result.get('notes') or []
        if not isinstance(children,list) or len(children)>11:raise UserError('La propuesta contiene demasiadas notas o una colección no válida.')
        total=len(root['body']);notes=[];ids={'source'}
        pages_allowed=set(c.get('media',{}).get('pages',[]))
        for child in children:
            key=child.get('id')
            if not isinstance(key,str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,59}',key) or key in ids:raise UserError('Las notas de la propuesta necesitan identificadores únicos.')
            ids.add(key)
            folder=child.get('folder')
            if folder not in folders:raise UserError('Una nota propone una carpeta que no existe.')
            typ=note_type(folder,child.get('note_type'))
            title=clean(child.get('title'),300).strip();body=clean(child.get('body'),50000).strip()
            if not title or not body:raise UserError('Una nota derivada no tiene título o contenido.')
            body=re.sub(r'!?\[\[([^\]]+)\]\]',lambda m:m.group(1).split('|')[-1],body)
            pages=child.get('pages') or []
            if not isinstance(pages,list) or any(type(n) is not int or n not in pages_allowed for n in pages):raise UserError('Una nota cita páginas fuera del contenido leído.')
            evidence=clean(child.get('source_evidence'),1500).strip()
            if not pages and (len(evidence)<15 or evidence not in c['text']):raise UserError('Una nota derivada no tiene una referencia verificable a la fuente. Regenera la propuesta.')
            images=child.get('images') or []
            if not isinstance(images,list) or any(type(n) is not int or not 0<=n<len(c['images']) for n in images):raise UserError('Una nota contiene una figura inexistente.')
            images=[n for n in dict.fromkeys(images) if n in root['selected_images']]
            note={**copy.deepcopy(root),'id':key,'title':title,'context':clean(child.get('context'),1000),'body':body,'folder':folder,
                  'note_type':typ,'filename':filename(c,title,folder,typ),'tags':self.app.tags(child.get('tags',[])),
                  'relations':self.validate_relations(c,child.get('relations',[]),candidates),'selected_images':images,
                  'source_pages':sorted(set(pages)),'source_evidence':evidence,'links':child.get('links') or [],'strategy':'study' if folder.startswith('07_Clases/') else 'concept'}
            total+=len(body);notes.append(note)
        if total>160000:raise UserError('La propuesta es demasiado extensa; pide una síntesis más compacta.')
        for note in notes:
            links=note['links']
            # Optional model suggestions must never introduce dangling links. The
            # verified source/section links are constructed independently below.
            note['links']=[{'id':v['id'],'reason':clean(v['reason'],700),'kind':v.get('kind') if v.get('kind') in RELATION_KINDS else 'relaciona'} for v in links
                           if isinstance(v,dict) and v.get('id') in ids and v['id']!=note['id']
                           and len(clean(v.get('reason')).strip())>=8] if isinstance(links,list) else []
        if notes and c.get('note_structure')=='single':
            # Validate children first, then keep all their content if the model
            # ignores the user's choice. Never silently drop generated sections.
            body='\n\n'.join([root['body'],*['## '+n['title']+'\n\n'+n['body'] for n in notes]])
            if len(body)>80000:raise UserError('La nota supera el tamaño permitido. Pide una síntesis más compacta o elige varias notas.')
            root['body']=body
            root['relations']=list({r['path']:r for r in root['relations']+[r for n in notes for r in n['relations']]}.values())
            root['tags']=self.app.tags(root['tags']+[tag for n in notes for tag in n['tags']])
            root['source_pages']=sorted({p for n in notes for p in n['source_pages']})
            root['strategy']='source'
            root['rationale']='Una sola nota, según tu elección; los apartados se conservan juntos.'
            if root['note_type']=='indice':
                root['note_type']='resumen' if root['folder'].startswith('07_Clases/') else 'fuente_externa'
                root['filename']=filename(c,root['title'],root['folder'],root['note_type'])
            notes=[]
        if notes:
            c['source_fingerprint']=c.get('source_fingerprint',c['fingerprint'])
            assigned={n for note in notes for n in note['selected_images']}
            root['selected_images']=[n for n in root['selected_images'] if n not in assigned]
            root['role']='index';root['strategy']='collection'
            c['bundle']={'rationale':root['rationale'],'notes':notes}
        else:
            c.pop('bundle',None)
            if c.get('source_fingerprint'):c['fingerprint']=c.pop('source_fingerprint')
        return root

    def drafts(self,c):return {'source':c['draft'],**{v['id']:v for v in c.get('bundle',{}).get('notes',[])}}

    def render_all(self,c,fields):
        from updates import Updates
        drafts=self.drafts(c);edits=fields.get('notes',{});selected=fields.get('selected_notes',list(drafts));active=fields.get('active_note','source');merged=fields.get('merged_into',{})
        if not isinstance(edits,dict) or any(k not in drafts for k in edits):raise UserError('La edición no corresponde a la propuesta.')
        if not isinstance(selected,list) or not selected or len(selected)!=len(set(selected)) or any(k not in drafts for k in selected):raise UserError('Selecciona las notas que quieres guardar.')
        if active not in drafts or not isinstance(merged,dict) or any(k not in drafts or v not in selected or k in selected or k==v for k,v in merged.items()):raise UserError('La integración de notas no es válida.')
        canonical=lambda k:merged.get(k,k)
        paths={};effective={};groups={k:[k]+[old for old,target in merged.items() if target==k] for k in drafts}
        for key in dict.fromkeys([*selected,active]):
            d=drafts[key];value=edits.get(key,{})
            if not isinstance(value,dict):raise UserError('Campos de nota no válidos.')
            folder=value.get('folder',d['folder']);typ=note_type(folder,value.get('note_type',d.get('note_type')));name=value.get('filename',d['filename'])
            if folder not in self.app.folders():raise UserError('Destino no admitido.')
            validate_filename(name,typ,folder);paths[key]=value.get('target_path') if value.get('save_mode')=='append' else folder+'/'+name
            if not isinstance(paths[key],str) or any(ch in paths[key] for ch in '[]|#^'):raise UserError('Ruta no válida para Obsidian.')
            effective[key]={**value,'note_type':typ}
            if value.get('save_mode')=='append':effective[key]['relations']=[p for p in value.get('relations',[]) if p!=paths[key]]
        if len({paths[k] for k in selected})!=len(selected):raise UserError('Dos notas utilizarían el mismo archivo.')
        excluded=set()
        for key,value in edits.items():
            for target in value.get('excluded_links',[]):
                if target not in drafts:raise UserError('Conexión interna desconocida.')
                excluded.add(tuple(sorted((canonical(key),canonical(target)))))
        rendered={}
        for key in dict.fromkeys([*selected,active]):
            d=copy.deepcopy(drafts[key]);links=[]
            if key=='source':links=[{'id':k,'reason':drafts[k].get('context') or 'Desarrollo de este apartado','kind':'amplia'} for k in selected if k!='source']
            else:
                if 'source' in selected:links.append({'id':'source','reason':'Síntesis y mapa de esta fuente','kind':'relaciona'})
                links.extend(v for member in groups[key] for v in drafts[member].get('links',[]))
            graph=[];planned=[];seen=set()
            for value in links:
                target=canonical(value['id'])
                if target not in selected or target==key or target in seen:continue
                seen.add(target);label=clean(edits.get(target,{}).get('title',drafts[target]['title']),300).replace('\n',' ');label=re.sub(r'[\[\]|]','',label)
                evidence=value.get('source_evidence','');target_evidence=value.get('target_evidence','')
                current_body=effective[key].get('body',d['body']);other_body=effective[target].get('body',drafts[target]['body'])
                valid=(not evidence or evidence in current_body) and (not target_evidence or target_evidence in other_body)
                accepted=tuple(sorted((canonical(key),target))) not in excluded and valid;kind=value.get('kind','relaciona')
                graph.append({'id':target,'title':label,'kind':kind,'reason':value['reason'],'accepted':accepted,'source_evidence':evidence,'target_evidence':target_evidence,'stale':not valid})
                if accepted:planned.append(f"- [[{paths[target].removesuffix('.md')}|{label}]] — {kind.capitalize()}: {clean(value['reason'],700)}")
            pages=sorted({p for member in groups[key] for p in drafts[member].get('source_pages',[])})
            d['source_pages']=pages
            local={**c,'draft':d,'_planned_links':planned,'_semantic_links':any(v['accepted'] and v['source_evidence'] for v in graph)}
            if key!='source' and pages:local['media']={'type':'section','pages':pages,'coverage':'Apunte de estas páginas de la fuente'}
            value=self.app.render(local,effective[key]);value['internal_links']=graph
            if effective[key].get('save_mode')=='append':value=Updates(self.app).render(c,value,effective[key])
            rendered[key]=value
        return rendered,selected,active

    def save_fingerprint(self,c,rendered,selected):
        source=c.get('source_fingerprint',c['fingerprint'])
        if not c.get('bundle') and selected==['source'] and not rendered['source'].get('update'):return source
        return hashlib.sha256(json.dumps([source,'collection-v1',sorted(rendered[k]['relative'] for k in selected)],ensure_ascii=False).encode()).hexdigest()

    def preview(self,c,fields):
        rendered,selected,active=self.render_all(c,fields);previous=c.get('save_intent',{});previous=previous.get('hashes',{}) if isinstance(previous,dict) else {};collisions=[]
        for key in selected:
            value=rendered[key];path=safe_path(self.app.vault(),value['relative'])
            if path.exists() and not value.get('update'):
                digest=hashlib.sha256(value['markdown'].encode()).hexdigest()
                if previous.get(value['relative'])!=digest or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:collisions.append(value['relative'])
        return {**{k:v for k,v in rendered[active].items() if k!='assets'},'duplicate':self.app.duplicate({**c,'fingerprint':self.save_fingerprint(c,rendered,selected)}),'collisions':collisions,'selected_count':len(selected),'update_count':sum(bool(rendered[k].get('update')) for k in selected),'updates_pending':[k for k in selected if rendered[k].get('update') and not rendered[k]['update']['approved']],'notes':[{'id':k,'relative':rendered[k]['relative']} for k in selected]}

    def save(self,c,fields):
        from publication import publish
        if c['status'] in ('saved','discarded'):raise UserError('Esta captura ya se ha guardado o descartado.')
        intent=c.get('save_intent',{});date=intent.get('date') if isinstance(intent,dict) else None
        c['_render_date']=date or dt.date.today().isoformat();c['_save_date']=c['_render_date'];rendered,selected,_=self.render_all(c,fields);c.pop('_render_date',None)
        c['source_fingerprint']=c.get('source_fingerprint',c['fingerprint']);c['fingerprint']=self.save_fingerprint(c,rendered,selected)
        if self.app.duplicate(c):raise UserError('Esta propuesta ya se ha guardado.')
        primary=publish(self.app,c,rendered,selected,write_new_atomic);c.pop('_save_date',None)
        c.update(status='saved',saved_path=primary,saved_paths=[rendered[k]['relative'] for k in selected]);self.app.store(c)
        return {'path':str(safe_path(self.app.vault(),primary)),'relative':primary,'paths':c['saved_paths'],'count':len(selected),'obsidian_url':'obsidian://open?vault='+quote(self.app.vault().name,safe='')+'&file='+quote(primary,safe='')}

"""Append-only amendments with explicit review and optimistic content checks."""
import hashlib
import re
from core import UserError,read_note,safe_path,clean
from translation import n

def digest(raw):return hashlib.sha256(raw).hexdigest()

class Updates:
    def __init__(self,app):self.app=app
    def prepare(self,c,path):
        from editorial import Editorial
        allowed={v['path'] for v in self.app.candidates(c)}|{r['path'] for n in Editorial(self.app).drafts(c).values() for r in n.get('relations',[])}|set(c.get('connections',{}).get('candidate_paths',[]))
        if path not in allowed:raise UserError('Elige una nota candidata verificada.')
        target=safe_path(self.app.vault(),path)
        if not target.is_file() or target.is_symlink():raise UserError('No se encuentra la nota existente.')
        raw=target.read_bytes()
        if len(raw)>500000:raise UserError('La nota es demasiado grande para revisar una ampliación.')
        c.setdefault('update_targets',{})[path]={'hash':digest(raw)};self.app.store(c)
        return {'path':path,'hash':digest(raw),'before':raw.decode('utf-8')}
    def render(self,c,rendered,fields):
        path=fields.get('target_path');known=c.get('update_targets',{}).get(path)
        if not known:raise UserError('Selecciona y revisa la nota existente antes de ampliarla.')
        target=safe_path(self.app.vault(),path);raw=target.read_bytes()
        # A recoverable publication may already contain precisely our amendment.
        intent=c.get('save_intent',{});updates=intent.get('updates',{}) if isinstance(intent,dict) else {}
        if path in updates and digest(raw)==intent.get('hashes',{}).get(path):
            backup=self.app.state/'update-backups'/c['id']/(digest(path.encode())+'.bak')
            raw=backup.read_bytes()
        if digest(raw)!=known['hash']:raise UserError('La nota existente cambió. Vuelve a seleccionarla y revisa la ampliación actualizada.')
        body=re.sub(r'^---\n[\s\S]*?\n---\n','',rendered['markdown']).lstrip()
        model=fields.get('revision_model') or c['draft'].get('model');method=n('Asistido por {model}',model=model) if model else n('Captura manual')
        # The note title becomes the heading of the amendment, followed by its provenance.
        body=re.sub(r'^#\s+(.+)\n',lambda m:n('## Aporte: {title}',title=m[1])+'\n'+n('\n> Aporte capturado el {date} · {method}\n',date=c['created'][:10],method=method),body,count=1)
        before=raw.decode('utf-8');addition=('' if before.endswith('\n\n') else '\n' if before.endswith('\n') else '\n\n')+body.strip()+'\n';after=before+addition
        review_hash=digest((known['hash']+after).encode())
        return {**rendered,'relative':path,'markdown':after,'update':{'expected':known['hash'],'review_hash':review_hash,'before':before,'addition':addition,'approved':fields.get('update_review_hash')==review_hash and fields.get('update_approved') is True}}

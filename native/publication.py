"""Recoverable mixed create/amend publication. Personal files are never truncated."""
import os
import tempfile
from core import UserError,safe_path
from updates import digest

def replace_checked(path,expected,raw):
    if not path.is_file() or path.is_symlink() or digest(path.read_bytes())!=expected:raise UserError('La nota cambió antes de guardar. Revisa de nuevo la ampliación.')
    fd,name=tempfile.mkstemp(prefix='.zen-amend-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.chmod(name,path.stat().st_mode & 0o777)
        if digest(path.read_bytes())!=expected:raise UserError('La nota cambió durante el guardado. No se ha reemplazado.')
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

def publish(app,c,rendered,selected,create):
    vault=app.vault();previous=c.get('save_intent',{});previous=previous if isinstance(previous,dict) else {}
    hashes={rendered[k]['relative']:digest(rendered[k]['markdown'].encode()) for k in selected};recovered=set();updates={}
    for key in selected:
        value=rendered[key];rel=value['relative'];path=safe_path(vault,rel);update=value.get('update')
        if update:
            if not update['approved']:raise UserError('Revisa y acepta cada ampliación antes de guardar.')
            updates[rel]=update['expected']
        if path.exists():
            current=digest(path.read_bytes())
            if previous.get('hashes',{}).get(rel)==hashes[rel] and current==hashes[rel]:recovered.add(rel)
            elif not update or current!=update['expected']:raise UserError('Ya existe una nota o ha cambiado desde la revisión. No se ha sobrescrito nada.')
        elif update:raise UserError('La nota que querías ampliar ya no existe.')
    for rel in previous.get('hashes',{}):
        if rel not in hashes and safe_path(vault,rel).exists():raise UserError('Recupera la misma selección de la escritura interrumpida antes de cambiarla.')
    backups=app.state/'update-backups'/c['id'];backups.mkdir(parents=True,exist_ok=True,mode=0o700)
    for rel,expected in updates.items():
        backup=backups/(digest(rel.encode())+'.bak')
        if not backup.exists():
            raw=safe_path(vault,rel).read_bytes()
            if digest(raw)!=expected:raise UserError('No se puede recuperar la versión anterior de la nota.')
            create(backup,raw)
    c['save_intent']={'hashes':hashes,'updates':updates,'date':c.get('_save_date')};app.store(c)
    created=[];amended=[];app.db.execute('BEGIN IMMEDIATE')
    try:
        if app.duplicate(c):raise UserError('La propuesta se guardó en otra ventana.')
        for rel,raw in {rel:raw for k in selected for rel,raw in rendered[k]['assets']}.items():
            path=safe_path(vault,rel);path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists():
                if path.read_bytes()!=raw:raise UserError('Un adjunto no coincide con su contenido.')
            else:create(path,raw);created.append((path,digest(raw)))
        for key in selected:
            value=rendered[key];rel=value['relative'];path=safe_path(vault,rel)
            if rel in recovered:continue
            if rel in updates:
                replace_checked(path,updates[rel],value['markdown'].encode());amended.append((path,rel))
            else:create(path,value['markdown'].encode());created.append((path,hashes[rel]))
        primary=rendered['source']['relative'] if 'source' in selected else rendered[selected[0]]['relative']
        import datetime
        app.db.execute('INSERT INTO saves VALUES (?,?,?)',(c['fingerprint'],primary,datetime.datetime.now().isoformat()));app.db.commit()
    except Exception:
        app.db.rollback()
        conflict=False
        for path,rel in reversed(amended):
            try:replace_checked(path,hashes[rel],(backups/(digest(rel.encode())+'.bak')).read_bytes())
            except UserError:conflict=True
        for path,expected in reversed(created):
            if path.exists() and digest(path.read_bytes())==expected:path.unlink()
            elif path.exists():conflict=True
        if conflict:raise UserError('Un archivo cambió durante la recuperación. Se ha conservado ese cambio; la versión anterior está en las copias locales de la captura.')
        raise
    return primary

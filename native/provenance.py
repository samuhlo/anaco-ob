"""Evidence-preserving source context, independent of hosting and reading order."""
import re
from pathlib import Path
from urllib.parse import urlsplit

FIELDS = ('origen', 'curso_fuente', 'modulo_aws', 'modulo_fuente', 'unidad_didactica',
          'seccion_fuente', 'tipo_recurso', 'fuente_autor', 'modulo')


def sanitize(value):
    if not isinstance(value, dict):
        return {}
    return {k: str(value[k])[:12000] for k in
            ('original_url', 'page_url', 'page_title', 'resource_title', 'description', 'breadcrumbs', 'headings', 'catalog', 'catalog_position')
            if isinstance(value.get(k), str) and value[k].strip()}


def evidence(c):
    return '\n'.join([c.get('title', ''), c.get('context', ''), *c.get('source_context', {}).values()])


def resolve(c, proposed=()):
    text = evidence(c)
    facts = {}
    # Structural labels only: transcript references to another course are not membership.
    if re.search(r'AWS (?:Academy )?Cloud Foundations', text, re.I):
        facts.update(origen='AWS Academy', curso_fuente='AWS Academy Cloud Foundations')
    if re.search(r'profesora', text, re.I):
        facts['origen'] = 'Profesora'
        facts.pop('curso_fuente', None)
    for pattern, key in ((r'\bMP\d{4}\b', 'modulo'), (r'\bUD\s*0*\d+\b', 'unidad_didactica')):
        matches = set(re.findall(pattern, text, re.I))
        if len(matches) == 1:
            facts[key] = matches.pop().upper().replace(' ', '')
    if facts.get('unidad_didactica'):
        facts['unidad_didactica'] = 'UD' + re.search(r'\d+', facts['unidad_didactica'])[0].zfill(2)
    if facts.get('curso_fuente'):
        numbers = set(re.findall(r'\b(?:Module|Módulo|Modulo)\s+0*(\d+)\b', text, re.I))
        if len(numbers) == 1:
            facts['modulo_aws'] = numbers.pop()
    sections = set(re.findall(r'\b(?:Section|Sección|Seccion|Apartados?)\s+(\d+(?:\s*(?:y|–|-)\s*\d+)?)\b', text, re.I))
    if len(sections) == 1:
        facts['seccion_fuente'] = sections.pop()
    # Model-supplied facts require both the value and a literal supporting excerpt.
    bank = text + '\n' + c.get('text', '')
    for item in proposed if isinstance(proposed, list) else []:
        if not isinstance(item, dict):
            continue
        key, value, quote = item.get('field'), item.get('value', ''), item.get('evidence', '')
        if key in FIELDS and isinstance(value, str) and isinstance(quote, str) and value and quote and quote in bank and value.casefold() in quote.casefold():
            facts.setdefault(key, value[:300])
    for label, pattern in (('caso de estudio', r'caso (?:de estudio|práctico)|case study'), ('demostración', r'demostraci[oó]n|\bdemo\b'), ('introducción', r'introducci[oó]n|introduction'), ('repaso', r'repaso|wrap.up|review')):
        if re.search(pattern, text, re.I):
            facts.setdefault('tipo_recurso', label)
    if facts.get('origen') == 'Profesora' or (facts.get('curso_fuente') and facts.get('seccion_fuente') and c.get('kind') == 'video'):
        facts.setdefault('tipo_recurso', 'clase')
    return facts


def title(c, value):
    f = c.get('provenance', {})
    parts = []
    if f.get('origen') == 'Profesora':
        parts = [f.get('modulo'), 'Profesora', f.get('unidad_didactica')]
    elif f.get('curso_fuente'):
        parts = [f['curso_fuente'].replace('AWS Academy', 'AWS')]
    if f.get('modulo_aws'):
        parts.append('M' + str(f['modulo_aws']).zfill(2))
    if f.get('seccion_fuente'):
        parts.append(('Apartado ' if f.get('origen') == 'Profesora' else 'S') + f['seccion_fuente'].zfill(2))
    return ' · '.join([p for p in parts if p and p.casefold() not in value.casefold()] + [value])[:300]


def route(app, c, fallback, folders):
    """Reuse a unique existing group, supported by its notes' source metadata."""
    from vault_scan import frontmatter
    f = c.get('provenance', {})
    keys = [k for k in ('curso_fuente', 'modulo_aws', 'unidad_didactica', 'modulo') if f.get(k)]
    if not keys or not f.get('origen'):
        return fallback
    found = set()
    for folder in folders:
        for path in (app.vault() / folder).glob('*.md'):
            if path.is_symlink():
                continue
            fm = frontmatter(path.read_text(errors='replace'))
            if all(str(fm.get(k, '')).casefold() == str(f[k]).casefold() for k in keys) and str(fm.get('origen', '')).startswith(f['origen']):
                found.add(folder)
                break
    if len(found) != 1:
        return fallback
    folder = next(iter(found))
    # Academic membership comes from the matched destination, never from AWS topic words.
    for path in (app.vault() / folder).glob('*.md'):
        fm = frontmatter(path.read_text(errors='replace')) if not path.is_symlink() else {}
        if all(str(fm.get(k, '')).casefold() == str(f[k]).casefold() for k in keys) and str(fm.get('origen', '')).startswith(f['origen']):
            for key in ('curso', 'asignatura', 'modulo', 'asignatura_nota'):
                if fm.get(key):
                    c['provenance'].setdefault(key, fm[key])
            break
    return folder


def properties(c):
    out = {'fuente_url': c['url'], 'fuente_titulo': c.get('source_context', {}).get('resource_title') or c['title'],
           'fuente_alojamiento': urlsplit(c['url']).hostname or 'archivo local'}
    if c['url'].startswith('local-file:'):
        out['fuente_archivo'] = out.pop('fuente_url')
    out.update(c.get('provenance', {}))
    if str(out.get('modulo_aws', '')).isdigit():
        out['modulo_aws'] = int(out['modulo_aws'])
    if c.get('author'):
        out.setdefault('fuente_autor', c['author'])
    for key, value in c.get('source_context', {}).items():
        out['fuente_' + key] = value
    if not out.get('curso_fuente') and not out.get('unidad_didactica'):
        out['contexto_pendiente'] = 'Curso, unidad y sección no identificados con certeza'
    elif not out.get('seccion_fuente'):
        out['contexto_pendiente'] = 'Sección de la fuente no identificada; sin numeración inventada'
    return out


def indexes(app, c, rendered, selected):
    """Append navigation without rewriting existing tables; publication backs it up."""
    from core import safe_path
    from updates import digest
    if not c.get('provenance'):
        return
    pending = {}
    for key in list(selected):
        note = rendered[key]
        if note.get('update'):
            continue
        parent = Path(note['relative']).parent
        for folder in (parent, *parent.parents):
            if str(folder) == '.':
                break
            path = safe_path(app.vault(), (folder / 'index.md').as_posix())
            if path.is_file() and not path.is_symlink():
                raw = path.read_text()
                rel = path.relative_to(app.vault()).as_posix()
                intent = c.get('save_intent', {})
                if isinstance(intent, dict) and intent.get('hashes', {}).get(rel) == digest(path.read_bytes()):
                    backup = app.state / 'update-backups' / c['id'] / (digest(rel.encode()) + '.bak')
                    if backup.is_file():
                        raw = backup.read_text()
                target = note['relative'].removesuffix('.md')
                if any(ch in target for ch in '[]|#^'):
                    break
                if target not in raw:
                    entry = pending.setdefault(path, [raw, []])
                    section = c.get('provenance', {}).get('seccion_fuente', 'sin sección conocida')
                    entry[1].append(f'- [[{target}]] — sección fuente: {section}; orden de lectura pendiente.')
                break
    for i, (path, (raw, lines)) in enumerate(pending.items()):
        key = '__index_' + str(i)
        rendered[key] = {'relative': path.relative_to(app.vault()).as_posix(), 'markdown': raw.rstrip() + '\n\n' + '\n'.join(lines) + '\n', 'assets': [],
                         'update': {'approved': True, 'expected': digest(raw.encode())}}
        selected.append(key)

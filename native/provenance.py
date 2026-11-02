"""Evidence-preserving source context, independent of hosting and reading order."""
import re
from pathlib import Path
from urllib.parse import urlsplit

FIELDS = ('origen', 'curso_fuente', 'modulo_aws', 'modulo_fuente', 'unidad_didactica',
          'seccion_fuente', 'tipo_recurso', 'fuente_autor', 'modulo')
SECTION = r'\b(?:Section|Sección|Seccion|Apartados?|(?-i:Ap))\s*(\d+(?:\s*(?:y|–|-)\s*\d+)?)\b'


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
    # Moodle codes join the module with underscores (…_ZE3IFC005500_MP5160_A), so \b is not enough.
    # Spellings of one unit (UD02, UD 2) are compared once normalized.
    for pattern, key, normal in ((r'(?<![A-Za-z0-9])MP\d{4}(?!\d)', 'modulo', str.upper),
                                 (r'(?<![A-Za-z0-9])UD\s*0*\d+(?!\d)', 'unidad_didactica', lambda m: 'UD' + str(int(re.search(r'\d+', m)[0])).zfill(2))):
        # The user's own intent ("apuntes de MP5160") names module and unit; the transcript does not.
        matches = {normal(m) for m in re.findall(pattern, text + '\n' + c.get('intent', ''), re.I)}
        if len(matches) == 1:
            facts[key] = matches.pop()
    if facts.get('curso_fuente'):
        numbers = set(re.findall(r'\b(?:Module|Módulo|Modulo)\s+0*(\d+)\b', text, re.I))
        if len(numbers) == 1:
            facts['modulo_aws'] = numbers.pop()
    # Drive files are named like "UD02-Apartado07-8.mp4": the number may follow the label directly.
    sections = {numbered(m) for m in re.findall(SECTION, text, re.I)}
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
    # The model may write the unit in words ("Unidad didáctica 2", "UD 2 - Modelos…").
    if facts.get('unidad_didactica') and (unit := re.search(r'\b(?:UD|Unidad(?:\s+did[aá]ctica)?)\s*0*(\d+)', facts['unidad_didactica'], re.I)):
        facts['unidad_didactica'] = 'UD' + unit[1].zfill(2)
    for label, pattern in (('caso de estudio', r'caso (?:de estudio|práctico)|case study'), ('demostración', r'demostraci[oó]n|\bdemo\b'), ('introducción', r'introducci[oó]n|introduction'), ('repaso', r'repaso|wrap.up|review')):
        if re.search(pattern, text, re.I):
            facts.setdefault('tipo_recurso', label)
    if facts.get('origen') == 'Profesora' or (facts.get('curso_fuente') and facts.get('seccion_fuente') and c.get('kind') == 'video'):
        facts.setdefault('tipo_recurso', 'clase')
    return facts


def numbered(value):
    """'07-8' -> '7–8'; None when the section is not written with numbers."""
    m = re.search(SECTION, value, re.I) or re.fullmatch(r'\s*(\d+(?:\s*(?:y|–|-)\s*\d+)?)\s*', value)
    if not m:
        return None
    return '–'.join(str(int(n)) for n in re.findall(r'\d+', m[1]))


def title(c, value):
    """Prefix only what identifies the note among its siblings, as the vault names them."""
    f = c.get('provenance', {})
    section = numbered(f.get('seccion_fuente', ''))
    if f.get('origen') == 'AWS Academy' and f.get('curso_fuente'):
        parts = [f['curso_fuente'].replace('AWS Academy', 'AWS')]
        if f.get('modulo_aws'):
            parts.append('M' + str(f['modulo_aws']).zfill(2))
        if section:
            parts.append('S' + section.zfill(2))
        return ' · '.join([p for p in parts if p.casefold() not in value.casefold()] + [value])[:300]
    unit = re.fullmatch(r'UD0*(\d+)', f.get('unidad_didactica', ''))
    if not unit:
        return value[:300]
    parts = ['UD' + unit[1]]
    numbers = section.split('–') if section else []
    if numbers:
        parts.append(('Apartados ' + ' y '.join(numbers)) if len(numbers) > 1 else 'Apartado ' + numbers[0])
    # Markers the model already wrote at the start are rebuilt once, in the vault's order.
    marker = r'(?:UD\s*0*' + unit[1] + r'|Apartados?\s*0*' + (r'\s*(?:y|–|-)\s*0*'.join(numbers) if numbers else r'\d+') + r')\b\s*[·:—–-]?\s*'
    rest = value
    while (m := re.match(marker, rest, re.I)):
        rest = rest[m.end():]
    if numbers and re.search(r'\bApartados?\s*0*' + numbers[0] + r'\b', rest, re.I):
        parts.pop()
    return (' · '.join(parts) + ': ' + rest)[:300] if rest else ' · '.join(parts)


def notes_in(app, folder):
    from vault_scan import frontmatter
    return [frontmatter(p.read_text(errors='replace')) for p in sorted((app.vault() / folder).glob('*.md')) if not p.is_symlink()]


def unit_route(app, c, fallback, folders):
    """The UDnn folder beside the unit folders of the same module, created when missing.

    MOTIVE -> a new unit has no notes yet, so only its siblings can say where it goes.
    Without a known module the single compatible tree is used only if the model
    pointed at it or at one of its ancestors: a "UD2" alone never moves a course."""
    f = c['provenance']
    wanted = re.fullmatch(r'UD(\d+)', f['unidad_didactica'])
    if not wanted:
        return None
    containers = {}
    for folder in folders:
        parent, _, name = folder.rpartition('/')
        if parent and re.fullmatch(r'UD\d+', name, re.I):
            containers.setdefault(parent, []).append(folder)
    fits = []
    for container, units in sorted(containers.items()):
        notes = [n for unit in units for n in notes_in(app, unit)]
        modules = {str(n.get('modulo', '')).casefold() for n in notes}
        if f.get('modulo') and f['modulo'].casefold() not in modules | {m.casefold() for m in re.findall(r'MP\d{4}', container)}:
            continue
        if f.get('origen') and notes and not any(str(n.get('origen', '')).startswith(f['origen']) for n in notes):
            continue
        fits.append((container, units, notes))
    near = [x for x in fits if fallback == x[0] or fallback.startswith(x[0] + '/')]
    if f.get('modulo') and len(fits) == 1:
        container, units, notes = fits[0]
    elif len(near) == 1:
        container, units, notes = near[0]
    elif len(fits) == 1 and fits[0][0].startswith(fallback + '/'):
        container, units, notes = fits[0]
    else:
        return None
    wanted = int(wanted[1])
    width = len(re.search(r'\d+', units[0].rpartition('/')[2])[0])
    folder = next((u for u in units if int(re.search(r'\d+', u.rpartition('/')[2])[0]) == wanted), container + '/UD' + str(wanted).zfill(width))
    if folder not in folders:
        # A unit folder the profile does not allow keeps the model's reviewable choice.
        if not app.vault_profile().rule(folder, required=False):
            return None
        c['planned_folders'] = [folder]
    for key in ('curso', 'asignatura', 'modulo', 'origen', 'asignatura_nota'):
        value = next((n[key] for n in notes if n.get(key)), None)
        if value:
            f.setdefault(key, value)
    return folder


def number(app, notes):
    """Continue the 'NN - ' file numbering where sibling notes already use it."""
    profile, last = app.vault_profile(), {}
    for note in notes:
        folder = note['folder']
        if not profile.pattern(folder, note['note_type']).startswith('{title}') or re.match(r'\d{2} - ', note['filename']):
            continue
        if folder not in last:
            path = app.vault() / folder
            names = [p.name for p in path.glob('*.md')] if path.is_dir() else []
            if not names and path.parent.is_dir():
                # A new unit folder follows the numbering of the units beside it.
                names = [p.name for sibling in path.parent.iterdir() if sibling.is_dir() and re.fullmatch(r'UD\d+', sibling.name, re.I) for p in sibling.glob('*.md')]
                found = [0] if any(re.match(r'\d{2} - ', n) for n in names) else []
            else:
                found = [int(m[1]) for n in names if (m := re.match(r'(\d{2}) - ', n))]
            last[folder] = max(found) if found else None
        if last[folder] is not None:
            last[folder] += 1
            note['filename'] = f'{last[folder]:02d} - ' + note['filename']


def renumber(app, folder, name, reserved=None):
    """A queued draft keeps its 'NN - ' place unless another note took that number meanwhile.

    reserved -> numbers already given to other notes of the same collection, by folder."""
    m, path = re.match(r'(\d{2}) - ', name), app.vault() / folder
    if not m or not path.is_dir():
        return name
    own = reserved.setdefault(folder, set()) if reserved is not None else set()
    taken = own | {int(x[1]) for p in path.glob('*.md') if p.name != name and (x := re.match(r'(\d{2}) - ', p.name))}
    number = max(taken) + 1 if int(m[1]) in taken else int(m[1])
    own.add(number)
    return f'{number:02d} - ' + name[m.end():]


def route(app, c, fallback, folders):
    """Reuse a unique existing group, supported by its notes' source metadata."""
    from vault_scan import frontmatter
    f = c.get('provenance', {})
    if f.get('unidad_didactica') and (folder := unit_route(app, c, fallback, folders)):
        return folder
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

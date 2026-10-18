"""Bounded, resumable ingestion and batched reading of HTML books."""
import base64
import hashlib
import json
import re
import shutil
import subprocess
import uuid
from pathlib import Path
from core import UserError, clean, image_bytes, json_dump, normalized_url


class Reader:
    def __init__(self, app):
        self.app = app

    def directory(self, identifier):
        if not re.fullmatch(r'[a-f0-9]{32}', str(identifier)):
            raise UserError('Extracción de libro no válida.')
        return self.app.state / 'readers' / identifier

    def load(self, identifier):
        directory = self.directory(identifier)
        meta = json.loads((directory / 'book.json').read_text())
        if meta['vault'] != str(self.app.vault()):
            raise UserError('Este libro pertenece a otro vault.')
        return directory, meta

    def begin(self, message):
        count = message.get('count')
        if type(count) is not int or not 1 <= count <= 500:
            raise UserError('El lector debe contener entre 1 y 500 páginas. No se ha extraído una parte del libro.')
        url = normalized_url(message.get('url', ''))
        identity = clean(message.get('identity'), 1000)
        if message.get('job'):
            directory, meta = self.load(message['job'])
            if (meta['url'], meta['count'], meta['identity']) != (url, count, identity):
                raise UserError('El contenido del lector cambió; vuelve a detectar el libro.')
            return {'job': directory.name, 'done': sorted(map(int, meta['pages']))}
        identifier = uuid.uuid4().hex
        directory = self.directory(identifier)
        directory.mkdir(parents=True, mode=0o700)
        json_dump(directory / 'book.json', {'vault': str(self.app.vault()), 'url': url,
                  'title': clean(message.get('title'), 300), 'count': count,
                  'identity': identity, 'html_context': clean(message.get('context'),150000), 'pages': {}, 'status': 'extracting'})
        return {'job': identifier, 'done': []}

    def page_begin(self, message):
        directory, meta = self.load(message['job'])
        index, size = message.get('index'), message.get('size', 0)
        if type(index) is not int or not 1 <= index <= meta['count'] or type(size) is not int or not 0 <= size <= 3_000_000:
            raise UserError('Página o tamaño no válido.')
        if str(index) in meta['pages']:
            return {'complete': True}
        page = {'index': index, 'size': size, 'text': clean(message.get('text'), 50000),
                'label': clean(message.get('label'), 200)}
        json_dump(directory / f'input-{index}.json', page)
        (directory / f'input-{index}.part').write_bytes(b'')
        return {'complete': False}

    def chunk(self, message):
        directory, meta = self.load(message['job'])
        index = message.get('index')
        if type(index) is not int or not 1 <= index <= meta['count']:
            raise UserError('Página no válida.')
        page = json.loads((directory / f'input-{index}.json').read_text())
        target = directory / f'input-{index}.part'
        try:
            raw = base64.b64decode(message.get('data', ''), validate=True)
        except (ValueError, TypeError) as exc:
            raise UserError('Fragmento del libro no válido.') from exc
        if len(raw) > 393216 or message.get('offset') != target.stat().st_size or target.stat().st_size + len(raw) > page['size']:
            raise UserError('Transferencia de página incompleta o desordenada.')
        with target.open('ab') as stream:
            stream.write(raw)
        return {'offset': target.stat().st_size}

    def page_finish(self, message):
        directory, meta = self.load(message['job'])
        index = message.get('index')
        if type(index) is not int or not 1 <= index <= meta['count']:
            raise UserError('Página no válida.')
        if str(index) in meta['pages']:
            return {'done': len(meta['pages']), 'total': meta['count']}
        page = json.loads((directory / f'input-{index}.json').read_text())
        part = directory / f'input-{index}.part'
        if part.stat().st_size != page['size']:
            raise UserError('Faltan datos de la página; vuelve a extraer el libro para continuar.')
        text, method = page['text'], 'Texto HTML'
        if page['size']:
            raw, ext = image_bytes({'data': base64.b64encode(part.read_bytes()).decode()})
            path = directory / f'page-{index}{ext}'
            part.replace(path)
            page['file'] = path.name
            page['digest'] = hashlib.sha256(raw).hexdigest()
            if len(text.strip()) < 120 and shutil.which('tesseract'):
                try:
                    from jobs import run_command
                    result = run_command(['tesseract', str(path), 'stdout', '-l', 'eng'],self.app.check_cancel,timeout=60)
                    ocr = result.stdout.decode(errors='replace').strip() if not result.returncode else ''
                    if ocr:
                        text = ocr if len(ocr) > len(text) else text
                        method = 'OCR local' if not page['text'].strip() else 'Texto HTML y OCR local'
                except subprocess.TimeoutExpired:
                    method = 'OCR pendiente; se requiere lectura visual'
        elif not text.strip():
            raise UserError(f'La página {index} no contiene texto ni una imagen legible. No se ha omitido en silencio.')
        page.update(text=text, method=method)
        page.pop('size', None)
        json_dump(directory / f'page-{index}.json', page)
        meta['pages'][str(index)] = {'file': page.get('file'), 'digest': hashlib.sha256((page.get('digest','')+text).encode()).hexdigest()}
        json_dump(directory / 'book.json', meta)
        (directory / f'input-{index}.json').unlink(missing_ok=True)
        part.unlink(missing_ok=True)
        return {'done': len(meta['pages']), 'total': meta['count']}

    def pages(self, directory, meta):
        missing = [n for n in range(1, meta['count'] + 1) if str(n) not in meta['pages']]
        if missing:
            raise UserError(f'Libro incompleto: faltan {len(missing)} páginas. Vuelve a extraer para continuar; las recibidas se conservan.')
        return [json.loads((directory / f'page-{n}.json').read_text()) for n in range(1, meta['count'] + 1)]

    def image(self, directory, page):
        return {'data': base64.b64encode((directory / page['file']).read_bytes()).decode(),
                'url': 'reader-page:' + str(page['index']), 'alt': f"Página {page['index']} del libro",
                'page': page['index'], 'visual_page': True}

    def finish(self, message):
        directory, meta = self.load(message['job'])
        pages = self.pages(directory, meta)
        if meta.get('capture'):
            return self.app.public(self.app.load(meta['capture']))
        text = (meta.get('html_context','')+'\n\n' if meta.get('html_context') else '')+'\n\n'.join(f"[Página {p['index']}]\n{p['text'] or 'Página gráfica; requiere lectura visual.'}" for p in pages)
        candidates = [p for p in pages if p.get('file')]
        candidates.sort(key=lambda p: (bool(re.search(r'diagram|figure|figura|esquema|architecture|table|gr[aá]fic', p['text'], re.I)), p['index'] in (1, meta['count'])), reverse=True)
        images, budget = [], 0
        for page in candidates:
            raw_size = (directory / page['file']).stat().st_size
            if len(images) >= 6:
                break
            if budget + raw_size <= 4_500_000:
                images.append(self.image(directory, page)); budget += raw_size
        no_text = [p['index'] for p in pages if not p['text'].strip()]
        warnings = []
        if no_text:
            warnings.append('Páginas sin texto HTML/OCR: ' + ', '.join(map(str, no_text)) + '. La lectura con IA visual las incluirá; el modo sin visión no puede leerlas.')
        capture = self.app.stage({'kind': 'article', 'url': meta['url'], 'title': meta['title'],
                  'text': text[:150000], 'images': images, 'warnings': warnings,
                  'reader': {'scope': 'complete'} })
        stored = self.app.load(capture['id'])
        stored['text'] = text
        stored['reader'] = {'job': directory.name, 'scope': 'captured', 'total_pages': meta['count'], 'captured_pages': len(pages)}
        stored['media'] = {'type': 'reader', 'total_pages': meta['count'], 'pages': list(range(1, meta['count'] + 1)),
                           'method': 'Texto HTML y OCR local; páginas gráficas guardadas para lectura completa por lotes',
                           'coverage': f"{len(pages)}/{meta['count']} páginas capturadas"}
        stored['fingerprint'] = hashlib.sha256(json.dumps([meta['vault'], meta['url'], meta['pages'],meta.get('html_context','')], sort_keys=True).encode()).hexdigest()
        self.app.store(stored)
        meta.update(capture=stored['id'], status='captured')
        json_dump(directory / 'book.json', meta)
        return self.app.public(stored)

    def generate(self, capture, candidates, folders):
        directory, meta = self.load(capture['reader']['job'])
        pages = self.pages(directory, meta)
        cfg = self.app.config()
        visual = cfg['describe_images'] and cfg['vision_policy'] != 'metadata'
        batch_size = cfg.get('reader_batch_pages', 6)
        if not visual and any(not p['text'].strip() for p in pages):
            raise UserError('Hay páginas gráficas sin texto. Activa visión para leer el libro completo; no se resumirá una parte como si fuera todo.')
        key = hashlib.sha256(json.dumps([meta['pages'], cfg['model'], cfg['vision_model'], visual, batch_size,
                                        capture.get('intent', ''), self.app.guide()['hash']], sort_keys=True).encode()).hexdigest()[:24]
        previous_profile=capture.get('draft',{}).get('profile_hash')
        previous_key=hashlib.sha256(json.dumps([meta['pages'],cfg['model'],cfg['vision_model'],visual,batch_size,capture.get('intent',''),previous_profile],sort_keys=True).encode()).hexdigest()[:24] if previous_profile else None
        summaries, captions, models = [], {}, set()
        for start in range(0, len(pages), batch_size):
            batch = pages[start:start + batch_size]
            self.app.progress(f"Leyendo páginas {batch[0]['index']}–{batch[-1]['index']} de {len(pages)}…")
            path = directory / f'analysis-{key}-{start}.json'
            legacy=directory/f'analysis-{previous_key}-{start}.json' if previous_key else None
            if not path.exists() and legacy and legacy.exists():json_dump(path,json.loads(legacy.read_text()))
            image_pages = [p for p in batch if p.get('file')] if visual else []
            if path.exists():
                result = json.loads(path.read_text())
            else:
                local = {**capture, 'id': capture['id'], 'reader': {'scope': 'batch', 'pages': [p['index'] for p in batch]},
                         'title': f"{capture['title']} · páginas {batch[0]['index']}–{batch[-1]['index']}",
                         'text': '\n\n'.join(f"[Página {p['index']}]\n{p['text'] or 'Leer la imagen adjunta de esta página.'}" for p in batch),
                         'images': [self.image(directory, p) for p in image_pages], 'warnings': [],
                         'selected_images': list(range(len(image_pages)))}
                result = self.app.codex_generate(local, [], folders)
                if not str(result.get('body','')).strip():
                    raise UserError('El lote no devolvió una lectura válida; reintenta la preparación.')
                described = {i.get('index'): i for i in result.get('image_captions', []) if isinstance(i, dict) and i.get('description')}
                if any(i not in described for i in range(len(image_pages))):
                    raise UserError(f"La lectura de las páginas {batch[0]['index']}–{batch[-1]['index']} quedó incompleta. Reintenta: los lotes anteriores están guardados.")
                json_dump(path, result)
            models.add(result.get('_model', cfg['vision_model'] if visual else cfg['model']))
            summaries.append(f"[Páginas {batch[0]['index']}–{batch[-1]['index']}]\n{clean(result.get('body'), 20000)}")
            for item in result.get('image_captions', []):
                index = item.get('index')
                if type(index) is int and 0 <= index < len(image_pages):
                    captions[image_pages[index]['index']] = item
        self.app.progress(f'Sintetizando las {len(pages)} páginas y buscando relaciones…')
        samples = '\n\n'.join(f"[Página {p['index']}, extracto literal]\n{p['text'][:650]}" for p in pages if p['text'])
        synthesis = {**capture, 'reader': {'scope': 'synthesis', 'total_pages': len(pages)},
                     'images': [], 'selected_images': [], 'available_figures':[{'index':i,'page':v.get('page'),'description':captions.get(v.get('page'),{}).get('description','')} for i,v in enumerate(capture['images'])], 'text': '\n\n'.join(summaries) + '\n\nTexto HTML adicional del lector:\n'+meta.get('html_context','')+'\n\nExtractos literales para verificar relaciones:\n' + samples}
        result = self.app.codex_generate(synthesis, candidates, folders)
        required = self.app.prepare_captions(capture)
        result['image_captions'] = []
        for index in required:
            item = captions.get(capture['images'][index].get('page'))
            if not item:
                raise UserError('Falta la descripción de una figura del libro. Reintenta la preparación.')
            result['image_captions'].append({**item, 'index': index})
        models.add(result.get('_model', cfg['model']))
        capture['reader']['analyzed_pages'] = len(pages)
        capture['media'].update(coverage=f"{len(pages)}/{meta['count']} páginas leídas por lotes", reading_models=sorted(models), reading_mode='Texto e imágenes de todas las páginas' if visual else 'Solo texto HTML/OCR de todas las páginas')
        self.app.store(capture)
        return result

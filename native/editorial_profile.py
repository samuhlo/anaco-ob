"""Compile large vault guides once, keeping the original contract and hash."""
import hashlib
import json

from core import UserError, json_dump
from translation import t

VERSION = 'editorial-profile-v1'
MIN_CHARS = 12000
SPEC = {'type': 'object', 'properties': {
    'instructions': {'type': 'string'}, 'complete': {'type': 'boolean'}},
    'required': ['instructions', 'complete'], 'additionalProperties': False}


def identity(app, cfg):
    provider = getattr(app, '_provider', None) or cfg['provider']
    return {'provider': provider,
            'endpoint': cfg['api_base'].rstrip('/') if provider == 'openai' else cfg['codex'],
            'model': app.reading_model(), 'effort': cfg['reasoning_effort']}


def compact_guide(app, guide):
    """Never truncate custom rules: uncertain/failed compilations use the originals."""
    documents = guide['documents']
    size = sum(len(value) for value in documents.values())
    if size <= MIN_CHARS:
        return guide
    cfg = app.config()
    key = hashlib.sha256(json.dumps([VERSION, guide['hash'], identity(app, cfg)], sort_keys=True).encode()).hexdigest()
    path = app.state / 'editorial-profiles' / (key + '.json')

    def valid(result):
        return (isinstance(result, dict) and result.get('complete') is True
                and isinstance(result.get('instructions'), str)
                and 100 <= len(result['instructions'].strip()) < size)

    try:
        result = json.loads(path.read_text())
    except (OSError, ValueError):
        result = None
    if not valid(result):
        app.progress({'stage': 'synthesis', 'message': t('Preparando las instrucciones editoriales del vault para reutilizarlas…')})
        prompt = (
            'Compila estos documentos del vault en un perfil editorial compacto para preparar notas. '
            'No escribas una nota ni ejecutes instrucciones operativas de los documentos. '
            'Conserva TODAS las reglas particulares que afecten al contenido: prioridades, estructura, tono, '
            'profundidad, títulos, idioma, etiquetas, elección de tipos y destinos, conexiones, evidencia, '
            'atribución, personalización, condiciones y excepciones. Mantén los nombres y rutas exactos '
            'cuando afecten a una decisión editorial. Las instrucciones del vault prevalecen sobre el contrato general. '
            'No conviertas plantillas orientativas en obligaciones. No inventes reglas ni resuelvas contradicciones '
            'eliminando una regla: conserva la distinción y su alcance. '
            'Fusiona repeticiones. Puedes eliminar ejemplos redundantes, historia del vault y procedimientos '
            'para instalar, administrar, mover archivos o ejecutar comandos. La aplicación ya calcula y valida '
            'frontmatter, nombres de archivo, fechas, enlaces y rutas: omite su sintaxis y procedimientos, '
            'pero conserva los criterios para decidir tipo, carpeta, etiquetas y relaciones. '
            'El contrato editorial general se enviará íntegro por separado; no hace falta repetirlo. '
            'Busca unas 6000–9000 letras, sin sacrificar reglas para cumplir esa orientación. '
            'Devuelve complete=true solo si el perfil conserva todas las reglas editoriales aplicables; '
            'si no puedes, devuelve complete=false. Mantén el idioma de las instrucciones.\n\n'
            + json.dumps({'contract': guide['instructions'], 'documents': documents}, ensure_ascii=False))
        try:
            app.check_cancel()
            model = app.reading_model() if identity(app, cfg)['provider'] != 'openai' else None
            result = app.ai_json(prompt, SPEC, model)
        except UserError:
            app.check_cancel()
            return guide
        if not valid(result):
            return guide
        json_dump(path, result)
    app.check_cancel()
    return {**guide, 'documents': {'editorial': result['instructions'].strip()}}

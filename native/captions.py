"""Resolve existing image descriptions without visual inference."""
import re
import unicodedata
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit
from translation import n

GENERIC=set('image images imagen imagenes imaxe foto photo picture screenshot captura screen shot figure figura fig diagram diagrama chart grafico ilustracion source fuente pendiente descripcion description untitled sin titulo page pagina pdf frame fotograma en del de la el the of a an y and hero desktop mobile tablet thumb thumbnail small large medium full scaled optimized resized retina final copy copia webp jpg jpeg png gif svg avif'.split())


def words(value):
    text=unicodedata.normalize('NFKD',value.lower())
    text=''.join(c for c in text if not unicodedata.combining(c))
    return re.findall(r'[a-z]{2,}',text)


def informative(value):
    value=re.sub(r'\s+',' ',str(value or '')).strip()
    meaningful=[w for w in words(value) if w not in GENERIC]
    if len(value)<12 or len(meaningful)<2:return ''
    if re.search(r'\.(?:png|jpe?g|webp|gif|svg|avif)(?:\?.*)?$',value,re.I):return ''
    if re.search(r'(?i)^(?:img|image|fig(?:ure)?|foto|captura|screenshot)[ _-]*\d*$',value):return ''
    return value[:1800]


def html_caption(image):
    # An explicit visible caption is more relevant than an accessibility fallback.
    for key in ('figcaption','aria_description','alt','aria_label','title'):
        text=informative(image.get(key))
        if text:return text,key
    return '', ''


def filename_hint(image):
    name=unquote(PurePosixPath(urlsplit(str(image.get('url') or '')).path).name)
    if not re.search(r'\.(?:png|jpe?g|webp|gif|svg|avif)$',name,re.I):return ''
    stem=name.rsplit('.',1)[0]
    if re.search(r'(?i)[a-f0-9]{12,}',stem):return ''
    stem=re.sub(r'([a-z])([A-Z])',r'\1 \2',stem)
    stem=re.sub(r'\d+[xX]\d+|@\d+x',' ',stem)
    stem=re.sub(r'[_\-\s]+',' ',stem).strip()
    useful=[w for w in words(stem) if w not in GENERIC and len(w)>=3]
    if len(set(useful))<2 or any(len(w)>24 for w in useful):return ''
    # Keep this explicitly labeled: a filename is a hint, not a visual observation.
    return n('Nombre del archivo: {name}.',name=stem[:200])

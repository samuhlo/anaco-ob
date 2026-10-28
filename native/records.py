"""Bounded, read-only record validation; never delete or rewrite damaged files."""
import datetime
import json
import math
import re


class RecordError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def read_record(path, validate=None, limit=32_000_000):
    if path.is_symlink():
        raise RecordError('symlink')
    try:
        with path.open('rb') as stream:
            raw = stream.read(limit + 1)
    except OSError as exc:
        raise RecordError('unreadable') from exc
    if len(raw) > limit:
        raise RecordError('too_large')
    try:
        value = json.loads(raw.decode('utf-8'))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise RecordError('invalid_json') from exc
    if not isinstance(value, dict) or validate and not validate(value):
        raise RecordError('invalid_record')
    return value


def capture_record(value, identifier):
    strings = ('id', 'vault', 'title', 'kind', 'created', 'status', 'text', 'url', 'fingerprint')
    if any(not isinstance(value.get(key), str) for key in strings):
        return False
    if value['id'] != identifier or not re.fullmatch(r'[a-f0-9]{32}', identifier):
        return False
    if not value['vault'] or not re.fullmatch(r'[a-f0-9]{64}', value['fingerprint']):
        return False
    if value['status'] not in ('pending', 'draft', 'saved', 'discarded'):
        return False
    if value['kind'] not in ('article', 'quote', 'image', 'pdf', 'video'):
        return False
    if not isinstance(value.get('images'), list) or any(not isinstance(i, dict) for i in value['images']):
        return False
    if value['status'] == 'draft' and (not isinstance(value.get('draft'), dict)
                                     or not isinstance(value['draft'].get('body'), str)):
        return False
    try:
        datetime.datetime.fromisoformat(value['created'])
    except ValueError:
        return False
    return True


def job_record(value, identifier):
    return (value.get('id') == identifier and bool(re.fullmatch(r'[a-f0-9-]{32,36}', identifier))
            and isinstance(value.get('vault'), str) and bool(value['vault'])
            and isinstance(value.get('request', {}), dict)
            and value.get('status') in ('running', 'pending', 'failed', 'interrupted', 'cancelled', 'complete', 'discarded')
            and type(value.get('updated', 0)) in (int, float)
            and math.isfinite(value.get('updated', 0)))


def issue(report, path, error):
    report['count'] += 1
    if len(report['records']) < 20:
        identifier = path.parent.name if path.name == 'job.json' else path.stem
        if not re.fullmatch(r'[a-f0-9-]{32,36}', identifier):
            identifier = None
        report['records'].append({'id': identifier, 'code': error.code})
